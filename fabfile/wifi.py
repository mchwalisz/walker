import re
from random import choice
from string import ascii_letters, digits
from fabric.api import *
import fabric.contrib.files as fabfiles


def myrun(cmd, out=False):
    if out:
        args = tuple()
    else:
        args = ('output', 'running')
    with hide(*args):
        if 'tplink' in env.host_string:
            with settings(shell='/bin/sh -c'):
                return run(cmd)
        else:
            return sudo(cmd)


def interfaces_list():
    devices = myrun('iw dev')
    for line in devices.split('\n'):
        line = line.strip()
        if line.startswith('Interface'):
            yield line.split(' ')[-1]


@task()
def create_ap(
        interface='wlan0',
        phy=None,
        ssid='twist-test',
        channel=40,
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
    with settings(hide('warnings', 'stdout', 'stderr'), warn_only=True):
        if phy is not None:
            myrun('ip dev {} del'.format(interface))
            myrun('iw {} interface add {} type managed'.format(phy, interface))
        else:
            myrun('iw dev {} set type managed'.format(interface))
        myrun('pkill -eF /tmp/hostapd-{}.pid'.format(interface))

    if bssid is None:
        mac = re.search('ether ([0-9a-f:]{17})',
            myrun('ip link show dev {}'.format(interface))).group(1)
        bssid = '02:' + mac[3:]
        context['bssid'] = bssid

    fabfiles.upload_template('hostapd.conf.jn2',
        '~/hostapd-{}.conf'.format(interface),
        context=context,
        template_dir='templates',
        use_jinja=True,
        backup=False)

    sudo(('hostapd -tB -P /tmp/hostapd-{0}.pid'
        ' -f /tmp/hostapd-{0}.log'
        ' ~/hostapd-{0}.conf').format(interface))
    sudo('ip addr add {}/24 dev {}'.format(ip, interface))


@task()
def connect(interface='wlan0',
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

    with settings(hide('warnings', 'stdout', 'stderr'), warn_only=True):
        if phy is not None:
            myrun('ip dev {} del'.format(interface))
            myrun('iw {} interface add {} type managed'.format(phy, interface))
        else:
            myrun('iw dev {} set type managed'.format(interface))
        myrun('pkill -eF /tmp/wpasup-{}.pid'.format(interface))

    fabfiles.upload_template('wpasup.conf.jn2',
        '~/wpasup.conf',
        context=context,
        template_dir='templates',
        use_jinja=True,
        backup=False)
    sudo('wpa_supplicant '
        + ' -c ~/wpasup.conf'
        + ' -D nl80211'
        + ' -i {}'.format(interface)
        + ' -P /tmp/wpasup-{}.pid'.format(interface)
        + ' -f /tmp/wpasup-{}.log'.format(interface)
        + ' -B'
         )
    sudo('ip addr add {}/24 dev {}'.format(ip, interface))


@task()
def scan():
    networks = []
    curr = None
    for iface in interfaces_list():
        myrun('ip link set {} up'.format(iface))
        with settings(
                hide('warnings', 'running', 'stdout', 'stderr'),
                warn_only=True):
            scan_result = myrun('iw dev {} scan'.format(iface))

        for line in scan_result.splitlines():
            line = line.strip()
            match = re.search(
                r'BSS (?P<bssid>([0-9a-f]{2}:?){6})\(on (?P<dev>\w*)\)',
                line)
            if match:
                if curr is not None:
                    networks.append(curr)
                curr = dict(
                    bssid=match.group('bssid'),
                    dev=match.group('dev'),
                    node=env.host_string.split('@')[-1])
            sgr = [
                ('freq', r'freq: (\d*)'),
                ('signal', r'signal: (.*)'),
                ('ssid', r'SSID: (.*)'),
            ]
            for name, pattern in sgr:
                match = re.search(pattern, line)
                if match:
                    curr[name] = match.group(1)

    networks = sorted(networks, key=lambda k: k['ssid'])
    scheme = '{:<17} {:<8} {:<5} {:<12} {:<10} {}'
    print(scheme.format('BSSID', 'dev', 'freq', 'signal', 'node', 'ssid'))
    for net in networks:
        print(scheme.format(
            net['bssid'],
            net['dev'],
            net['freq'],
            net['signal'],
            net['node'],
            net['ssid'],
        ))


@task()
def interfaces_create():
    with settings(warn_only=True, quiet=True):
        myrun('pkill -e hostapd', out=True)
        myrun('pkill -e wpa_supplicant', out=True)
    for iface in interfaces_list():
        myrun('iw dev {} del'.format(iface), out=True)
    phy_match = re.findall('Wiphy (\w*)',
        myrun('iw phy'),
        re.MULTILINE)
    for phy in phy_match:
        myrun(('iw phy {} interface ' +
            'add {} type managed').format(phy, 'wlan' + phy[-1]),
            out=True)
        myrun(('iw phy {} interface ' +
            'add {} type monitor').format(phy, 'mon' + phy[-1]),
            out=True)


@task()
def clean():
    with settings(warn_only=True, quiet=True):
        myrun('pkill -e hostapd', out=True)
        myrun('pkill -e wpa_supplicant', out=True)
    sudo('modprobe -r ath9k')
    sudo('modprobe ath9k')


@task()
def info(prefix='.'):
    host = env.host_string.split('@')[-1]
    phy_match = re.findall('Wiphy (\w*)',
        myrun('iw phy'))
    for phy in phy_match:
        phy_info = myrun('iw phy {} info'.format(phy))
        udevadm = myrun('udevadm info /sys/class/ieee80211/{}'.format(phy))
        pci = re.search(r'^P:.*?(\d{4}:\d{2}:\d{2}.\d)', udevadm).group(1)
        lspci = myrun('lspci -vvnnD -s {}'.format(pci))
        udevadmall = myrun(
            'udevadm info -a /sys/class/ieee80211/{}'.format(phy))
        with open('{}/{}-{}.info'.format(
                prefix, host, phy), 'w') as f:
            f.write('# iw info\n')
            f.write(phy_info)
            f.write('\n\n# lcpci -vvnnD -s \n')
            f.write(lspci)
            f.write('\n\n# udevadm info -a\n')
            f.write(udevadmall)




# iw phy0 interface add wlan0 type managed
# iw phy1 interface add wlan1 type managed
#
# ip link set wlan0 up
# ip link set wlan1 up
