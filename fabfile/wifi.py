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


ap_settings = dict(
    hw_mode='a',
    channel=52,
    interface='wlan1',
    psk=''.join([
        choice(ascii_letters + digits) for n in xrange(32)]),
    ssid='twist-test',
    bssid=None,
)


@task()
def create_ap(iface=None):
    'Creates Wi-Fi AP with hostapd'
    if iface is None:
        iface = ap_settings['interface']
    # TODO: create interface

    if ap_settings['bssid'] is None:
        mac = re.search('ether ([0-9a-f:]{17})',
            myrun('ip link show dev {}'.format(iface))).group(1)
        ap_settings['bssid'] = '02:' + mac[3:]

    with settings(warn_only=True, quiet=True):
        myrun('pkill -eF /tmp/hostapd-{}.pid'.format(iface))

    # dev <devname> interface add <name> type <type>
    ap_settings['interface'] = iface
    fabfiles.upload_template('hostapd.conf.jn2',
        '/tmp/hostapd-{}.conf'.format(iface),
        context=ap_settings,
        template_dir='templates',
        use_jinja=True)
    sudo(('hostapd -tB -P /tmp/hostapd-{0}.pid' +
        ' -f /tmp/hostapd-{0}.log'
        ' /tmp/hostapd-{0}.conf').format(iface))
    # TODO: configure IP


@task()
def scan():
    networks = []
    curr = None
    for iface in interfaces():
        myrun('ip link set {} up'.format(iface))
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


@task()
def connect():
    # TODO: upload wpa_supplicant config template
    # TODO: config IP
    pass


# iw phy0 interface add wlan0 type managed
# iw phy1 interface add wlan1 type managed
#
# ip link set wlan0 up
# ip link set wlan1 up
