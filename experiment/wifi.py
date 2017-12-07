
import re
import time

from collections import namedtuple
from fabric import Connection
from invoke.exceptions import UnexpectedExit
from io import StringIO
from jinja2 import Environment
from jinja2 import FileSystemLoader
from pathlib import Path
from typing import Optional

template_path = (Path(__file__).parent / '..' / 'templates').resolve()
jinja_env = Environment(loader=FileSystemLoader([template_path]))
WiFiDev = namedtuple('WiFiDev', 'phy, interface')


def phy_resolve(cnx, phy):
    """Resolves physical interface name.

    `phy` can be either physical interface name, or a PCI bus name.
    """
    result = cnx.run('ls -alh /sys/class/ieee80211/', hide=True)
    for line in result.stdout.split('\n'):
        if phy in line:
            phy_dev = line.strip().split('/')[-1]
            return phy_dev
    else:
        raise AttributeError('Could not find device')


def ifaces(cnx):
    """Generator for all wireless interfaces on the system"""
    for line in cnx.run('iw dev', hide=True).stdout.split('\n'):
        line = line.strip()
        if line.startswith('Interface'):
            iface = line.split(' ')[-1]
            result = cnx.run(f'iw dev {iface} info', hide=True)
            match = re.search('wiphy (\d+)', result.stdout)
            phy = 'phy' + match.group(1)
            yield WiFiDev(phy, iface)


def phy_check(cnx, phy=None, interface=None, suffix='w'):
    """Resolves physical and device interface mess.

    `phy` can be either physical interface name, or a PCI bus name.
    If `phy` is given, it will destroy all interfaces and create a new one with
    `interface` name (if none one will be generated based on `suffix`)

    If `phy` is None, then interface must be given and must exist. It will
    resolve to which physical device given `interface` belongs.
    """
    if phy:
        phy = phy_resolve(cnx, phy)
        if interface is None:
            interface = phy + suffix
        # Clean interfaces
        phy_clean(cnx, phy)
        cnx.sudo(f'iw {phy} interface add {interface} type managed')
        return WiFiDev(phy, interface)

    if interface is None:
        raise AttributeError('Either phy or interface must be set')
    try:
        result = cnx.run(f'iw dev {interface} info', hide=True)
        match = re.search('wiphy (?P<dev>\d+)', result.stdout)
        phy = 'phy' + match.group(1)
        # cnx.sudo(f'iw {interface} del')
    except UnexpectedExit as e:
        if e.result.exited == 237:
            raise AttributeError(f'No such interface ({interface})') from e
        else:
            raise
    return WiFiDev(phy, interface)


def phy_clean(cnx, phy):
    """Removes all interfaces for given `phy` device."""
    phy = phy_resolve(cnx, phy)
    for dev in ifaces(cnx):
        if phy == dev.phy:
            cnx.sudo(f'iw {dev.interface} del')
    cnx.sudo(f'pkill -f hostapd.*{phy}', warn=True)
    cnx.sudo(f'pkill -f wpa_supplicant.*{phy}', warn=True)


def info(cnx):
    """Print information about all devices"""
    # cnx.run('lshw -C network')
    results = cnx.run('lspci -nnk | grep "Wireless" -A2', hide=True)
    for connection, result in results.items():
        print(connection.host)
        print(result.stdout)


def reload(cnx):
    """Reload kernel modules for `ath9k`"""
    custom_modules = [
        'cfg80211',
        'mac80211',
        'ath',
        'ath9k_hw',
        'ath9k_common',
        'ath9k',
    ]

    for mod in reversed(custom_modules):
        cnx.sudo('rmmod -f {}'.format(mod), warn=True)
    for mod in custom_modules:
        cnx.sudo('modprobe {}'.format(mod))


def create_ap(
        cnx: Connection,
        phy: Optional[str] = None,
        interface: Optional[str] = None,
        ssid='experiment',
        channel=1,
        psk=None,
        bssid=None,
        ip='10.1.1.1'):
    """Creates Wi-Fi AP with hostapd.

    Args:
        phy (str): Physical device. Either name or PCI bus
        interface (str): Wi-Fi interface
        ssid (str): Network name
        channel (int): Used channel
        psk (str): Password
        bssid (str): Used BSSID, will be generated if None
        ip (str): IP address of the AP

    Returns:
        WiFiDev: information about used device
    """
    phy, interface = phy_check(cnx, phy, interface, '_ap')

    result = cnx.sudo(f'pkill -f hostapd.*{phy}', warn=True)
    if result:
        time.sleep(2)

    tmpl = jinja_env.get_template('hostapd.conf.jn2')
    cnx.put(
        StringIO(tmpl.render({
            'channel': channel,
            'hw_mode': 'g' if channel < 15 else 'a',
            'interface': interface,
            'ssid': ssid,
            'bssid': bssid,
            'psk': psk})),
        f'hostapd-{interface}.conf',
    )

    # Clean up interface
    cnx.sudo(f'ip link set {interface} down')
    cnx.sudo(f'ip addr flush dev {interface}')
    cnx.sudo(f'iw dev {interface} set type managed')

    cnx.sudo((f'hostapd -tB -P /tmp/hostapd-{phy}.pid'
        f' -f /tmp/hostapd-{interface}.log'
        f' ~/hostapd-{interface}.conf'))
    cnx.sudo(f'ip addr add {ip}/24 dev {interface}')
    cnx.run('echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward', hide=True)
    return WiFiDev(phy, interface)


def connect(
        cnx: Connection,
        phy: Optional[str] = None,
        interface: Optional[str] = None,
        ssid='tsch',
        psk=None,
        ip=None):
    """Task to connect a node to an AP.

    Args:
        interface (str): Wi-Fi interface
        phy (str): Physical device. If not None it will force create new
            interface on this device.
        phy_irq (str): Uniquely identify physical device by interrupt handler.
        ssid (str): Network name
        psk (str): Password
        ip (str): IP address of the AP

    Returns:
        WiFiDev: information about used device
    """
    phy, interface = phy_check(cnx, phy, interface, '_sta')

    if ip is None:
        ip_hash = hash(cnx.host) % 2**8
        ip = f'10.1.1.{ip_hash}'

    result = cnx.sudo(f'pkill -f wpa_supplicant.*{phy}', warn=True)
    if result:
        time.sleep(2)

    # Clean up interface
    cnx.sudo(f'ip link set {interface} down')
    cnx.sudo(f'ip addr flush dev {interface}')
    cnx.sudo(f'iw dev {interface} set type managed')

    tmpl = jinja_env.get_template('wpasup.conf.jn2')
    cnx.put(
        StringIO(tmpl.render({
            'interface': interface,
            'ssid': ssid,
            'psk': psk})),
        f'wpasup-{interface}.conf',
    )

    cnx.sudo((f'wpa_supplicant '
        f' -c ~/wpasup-{interface}.conf'
        f' -D nl80211'
        f' -i {interface}'
        f' -P /tmp/wpasup-{phy}.pid'
        f' -f /tmp/wpasup-{interface}.log'
        f' -B'))
    cnx.sudo(f'ip addr add {ip}/24 dev {interface}')
    return WiFiDev(phy, interface)
