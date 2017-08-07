import time
import datetime as dt
import fabric
from fabric.api import *
import re
import json
from pprint import pprint


@task()
def status(slice='wifi-channel', wait_for=None):
    """Gets slice status

    Args:
        slice: slice name to check
        wait_for: this value be True on all nodes `geni_operational_status`

    Returns: node info as dict
    """

    def parse_status(output):
        re_nodes = re.compile(
            r'client_id=\\\"(?P<name>\w*).*?sliver_id=\\\"(?P<sliver>.*?)\\\"')
        re_slivers = re.compile(
            r'\"geni_slivers\":\s(?P<json>\[.*?\])', re.MULTILINE | re.DOTALL)
        slivers = {node.group('sliver'): node.group('name')
            for node in re_nodes.finditer(output)}
        slivers_status = json.loads(re_slivers.search(output).group('json'))
        nodes = {}
        for sliver in slivers_status:
            urn = sliver['geni_sliver_urn']
            name = slivers[urn]
            nodes[name] = sliver
        return nodes

    args = '-V3 -a twist'
    checkcmd = 'omni describe {args} {slice}'.format(
        args=args,
        slice=slice)
    check = local(checkcmd, capture=True)
    nodes = parse_status(check.stderr)
    if wait_for:
        while not all(node['geni_operational_status'] == wait_for
                    for node in nodes.values()):
            for host in sorted(nodes):
                print("{}: {}".format(
                    host, nodes[host]['geni_operational_status']))
            time.sleep(10)
            check = local(checkcmd, capture=True)
            nodes = parse_status(check.stderr)
    else:
        pprint(nodes)
    return nodes


@task(default=True)
@hosts('localhost')
def set_hosts(slice='wifi-channel'):
    nodes = status(slice=slice, wait_for='geni_ready')
    hosts = list(nodes.keys())
    hosts = ['root@' + name if name.startswith('tplink') else name
        for name in hosts]
    with settings(
            host_string=hosts[0],
            shell='/bin/sh -c'), hide('output', 'running'):
        try:
            run('ls')
        except fabric.exceptions.NetworkError:
            env.gateway = 'proxyuser@api.twist.tu-berlin.de:2222'
    env.hosts.extend(hosts)


@task()
@parallel()
def install():
    if 'tplink' in env.host_string:
        install_openwrt()
        return
    sudo('apt install -yq'
        + ' wpasupplicant'
        + ' tcpdump'
        + ' python-setuptools'
        + ' python-pip'
        + ' iperf'
         )
    sudo('pip install pyric')
    sudo('iw reg set DE')


@task()
@parallel()
def install_openwrt():
    with settings(shell='/bin/sh -c'):
        run('opkg update')
        run('opkg install '
            + ' tcpdump'
            + ' python-setuptools'
            + ' python-pip'
            + ' iperf'
            + ' openssh-sftp-server'
            + ' procps-pkill'
            )
        run('pip install pyric')
        run('iw reg set DE')


@task()
def reserve(rspec='nucs.rspec', slice='wifi-channel', duration=8):
    '''Reserve twist resources (if necessary)

    Args:
        duration (int): Reservation duration in hours.
    '''
    args = '-V3 -a twist'
    end = dt.datetime.utcnow() + dt.timedelta(hours=int(duration))
    end = end.strftime('%Y%m%dT%H:%M:%S%Z')
    checkcmd = 'omni status {args} {slice}'.format(
        args=args,
        slice=slice)
    with settings(warn_only=True):
        if local(checkcmd, capture=True).stderr.find('geni_ready') != -1:
            print('Resources ready')
            return

    # Reserve and start
    local('omni createslice {slice}'.format(
        slice=slice))
    local('omni renewslice {slice} {end}'.format(
        slice=slice,
        end=end))
    alloc = local('omni allocate {args} {slice} rspecs/{rspec}'.format(
        args=args,
        rspec=rspec,
        slice=slice), capture=True)
    if alloc.stderr.find('Error') != -1:
        print(alloc.stderr)
        abort('Resources are not available')
    local('omni provision {args} {slice}'.format(
        args=args,
        slice=slice))
    execute(status, wait_for='geni_notready', slice=slice)
    local('omni performoperationalaction {args} {slice} geni_start'.format(
        args=args,
        slice=slice))

    execute(status, wait_for='geni_ready', slice=slice)


@task()
def release(slice='wifi-channel'):
    args = '-V3 -a twist'
    local('omni delete {args} {slice}'.format(
        args=args,
        slice=slice))
    # NOT supported
    # local('omni deleteslice {slice}'.format(
    #     slice=slice))


@task()
def remote():
    'Set config for remote work'
    env.gateway = 'proxyuser@api.twist.tu-berlin.de:2222'


@task()
@parallel()
def sanity_check():
    with settings(
            hide('warnings', 'stderr'),
            shell='/bin/sh -c',
            warn_only=True):
        run('cat /etc/twistprotected')


@task()
@hosts('localhost')
def restart(slice='wifi-channel'):
    args = '-V3 -a twist'
    nodes = execute(status, slice=slice, hosts='localhost')['localhost']
    for host in env.hosts:
        host = host.replace('root@', '').strip()
        local(('omni performoperationalaction {args}'
            + ' -u {urn} {slice} geni_restart').format(
            args=args,
            slice=slice,
            urn=nodes[host]['geni_sliver_urn']))
    execute(status, wait_for='geni_ready', slice=slice, hosts='localhost')
