import re
from random import choice
from itertools import product
from string import ascii_letters, digits
from fabric.api import *
import fabric.contrib.files as fabfiles


class FabricRunException(Exception):
    pass


def sudo_(cmd, out=False):
    if out:
        args = tuple()
    else:
        args = ('warnings', 'stdout', 'stderr')
    with hide(*args):
        if 'tplink' in env.host_string:
            with settings(shell='/bin/sh -c', user='root'):
                return run(cmd)
        else:
            return sudo(cmd)


@task
@parallel
def ifaces_create(phys=None, types_=('managed',)):
    if phys is None:
        phys = re.findall('Wiphy (\S*)',
            sudo_('iw phy'),
            re.MULTILINE)
    name_prefix = {
        'managed': 'w',
        'ibss': 'i', 'monitor': 'i',
        'mesh': 's',
        'wds': 'd'}
    for phy, type_ in product(phys, types_):
        sudo_(('iw phy {} interface ' +
            'add {} type {}').format(
            phy, name_prefix[type_] + phy[-1], type_))


@task
@parallel
def ifaces_clean():
    with settings(warn_only=True):
        sudo_('wifi down')
        sudo_('pkill hostapd')
        sudo_('pkill wpa_supplicant')
    for iface in ifaces_get():
        sudo_('iw dev {} del'.format(iface))


def ifaces_get():
    devices = sudo_('iw dev')
    for line in devices.split('\n'):
        line = line.strip()
        if line.startswith('Interface'):
            yield line.split(' ')[-1]


@task
@parallel
def phys_get():
    phy_list = sudo_('iw phy')
    phys = [phy.group('phy')
        for phy in re.finditer(r'Wiphy\s(?P<phy>\S*)', phy_list.stdout)]
    # phys.append(sudo_('hostname'))
    return phys


@task
def create_ap(
        interface=None,
        phy=None,
        ssid='twist-test',
        channel=48,
        hw_mode='a',
        psk='dUnZQFgqkYron1rKiLPGq4CVfToL9RuZ',
        bssid=None,
        ip='10.100.1.1'):
    """Task to create Wi-Fi AP with hostapd on a node.

    Args:
        interface (str): Wi-Fi interface
        phy (str): Physical device. If not None it will force create new
            interface on this device.
        ssid (str): Network name
        channel (int): Used channel
        hw_mode (str): Hardware modes
        psk (str): Password
        bssid (str): Used BSSID, will be generated if None
        ip (str): IP address of the AP
    """
    context = locals()
    if interface is None and phy is None:
        raise AttributeError('One of interface or phy must be provided')
    if interface is None:
        interface = 'w' + phy
        context['interface'] = interface
    with settings(hide('warnings', 'stdout', 'stderr'), warn_only=True):
        if phy is not None:
            sudo_('ip dev {} del'.format(interface))
            sudo_('iw {} interface add {} type managed'.format(phy, interface))
        else:
            sudo_('iw dev {} set type managed'.format(interface))
        sudo_('pkill /tmp/hostapd-{}.pid'.format(interface))

    if bssid is None:
        mac = re.search('ether ([0-9a-f:]{17})',
            sudo_('ip link show dev {}'.format(interface))).group(1)
        bssid = '02:' + mac[3:]
        context['bssid'] = bssid

    fabfiles.upload_template('hostapd.conf.jn2',
        '~/hostapd-{}.conf'.format(interface),
        context=context,
        template_dir='templates',
        use_jinja=True,
        backup=False)

    with settings(abort_exception=FabricRunException):
        sudo_(('hostapd -tB -P /tmp/hostapd-{0}.pid'
            ' -f /tmp/hostapd-{0}.log'
            ' ~/hostapd-{0}.conf').format(interface))
    sudo_('ip addr add {}/24 dev {}'.format(ip, interface))


@task
def connect(interface=None,
        phy=None,
        ssid='twist-test',
        psk='dUnZQFgqkYron1rKiLPGq4CVfToL9RuZ',
        ip='10.100.1.2'):
    """Task to connect a node to an AP.

    Args:
        interface (str): Wi-Fi interface
        phy (str): Physical device. If not None it will force create new
            interface on this device.
        ssid (str): Network name
        psk (str): Password
        ip (str): IP address of the AP
    """
    context = locals()
    if interface is None and phy is None:
        raise AttributeError('One of interface or phy must be provided')
    if interface is None:
        interface = 'w' + phy[-1]
        context['interface'] = interface

    with settings(warn_only=True):
        sudo_('pkill /tmp/wpasup-{}.pid'.format(interface))
        sudo_('rfkill unblock wifi')
        if phy is not None:
            sudo_('ip dev {} del'.format(interface))
            sudo_('iw {} interface add {} type managed'.format(phy, interface))
        else:
            sudo_('iw dev {} set type managed'.format(interface))

    fabfiles.upload_template('wpasup.conf.jn2',
        '~/wpasup-{}.pid'.format(interface),
        context=context,
        template_dir='templates',
        use_jinja=True,
        backup=False)
    sudo_('wpa_supplicant '
        + ' -c ~/wpasup-{}.pid'.format(interface)
        + ' -D nl80211'
        + ' -i {}'.format(interface)
        + ' -P /tmp/wpasup-{}.pid'.format(interface)
        + ' -f /tmp/wpasup-{}.log'.format(interface)
        + ' -B')
    sudo_('ip addr add {}/24 dev {}'.format(ip, interface))


@task
@parallel
def scan(log=False):
    """Returns scan of networks
    """
    networks = []
    curr = None
    for iface in ifaces_get():
        sudo_('ip link set {} up'.format(iface))
        with settings(warn_only=True):
            scan_result = sudo_('iw dev {} scan'.format(iface))

        for line in scan_result.splitlines():
            line = line.strip()
            match = re.search(
                r'BSS (?P<bssid>([0-9a-f]{2}:?){6})\(on (?P<dev>\w*)\)',
                line)
            if match:
                if (curr is not None) and ('ssid' in curr):
                    networks.append(curr)
                curr = dict(
                    bssid=match.group('bssid'),
                    sta_dev=match.group('dev'),
                    sta=env.host_string.split('@')[-1])
            sgr = [
                ('freq', r'freq: (\d*)'),
                ('signal', r'signal: (.*)'),
                ('ssid', r'SSID: (.*)'),
            ]
            for name, pattern in sgr:
                match = re.search(pattern, line)
                if match:
                    curr[name] = match.group(1)

    if log:
        scheme = '{:<17} {:<8} {:<5} {:<12} {:<10} {}'
        print(scheme.format('BSSID', 'dev', 'freq', 'signal', 'sta', 'ssid'))
        for net in sorted(networks, key=lambda k: k['ssid']):
            print(scheme.format(
                net['bssid'],
                net['sta_dev'],
                net['freq'],
                net['signal'],
                net['sta'],
                str(net['ssid']),
            ))
    return networks


@task
@parallel
def clean():
    """Makes sure hostapd and wpa_supplicant are killed and ath9k module
    reloaded
    """
    with settings(warn_only=True, quiet=True):
        sudo_('pkill hostapd', out=True)
        sudo_('pkill wpa_supplicant', out=True)
    sudo_('modprobe -r ath9k')
    sudo_('modprobe ath9k')


@task
def info(prefix='.'):
    'Gather node info to files'
    host = env.host_string.split('@')[-1]
    phy_match = re.findall('Wiphy (\w*)',
        sudo_('iw phy'))
    for phy in phy_match:
        phy_info = sudo_('iw phy {} info'.format(phy))
        udevadm = sudo_('udevadm info /sys/class/ieee80211/{}'.format(phy))
        pci = re.search(r'^P:.*?(\d{4}:\d{2}:\d{2}.\d)', udevadm).group(1)
        lspci = sudo_('lspci -vvnnD -s {}'.format(pci))
        udevadmall = sudo_(
            'udevadm info -a /sys/class/ieee80211/{}'.format(phy))
        with open('{}/{}-{}.info'.format(
                prefix, host, phy), 'w') as f:
            f.write('# iw info\n')
            f.write(phy_info)
            f.write('\n\n# lcpci -vvnnD -s \n')
            f.write(lspci)
            f.write('\n\n# udevadm info -a\n')
            f.write(udevadmall)
