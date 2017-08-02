import time
import datetime as dt
import fabric
from fabric.api import *
import re


@task()
def status(slice='wifi-channel', wait=False, wait_for='geni_ready'):
    args = '-V3 -a twist'
    checkcmd = 'omni describe {args} {slice}'.format(
        args=args,
        slice=slice)
    allocation_status = re.compile(
        '\"geni_allocation_status\":\s*\"(?P<status>\w*?)\"')
    operational_status = re.compile(
        '\"geni_operational_status\":\s*\"(?P<status>\w*?)\"')

    check = local(checkcmd, capture=True)
    print([m.group('status')
        for m in allocation_status.finditer(check.stderr)])
    print([m.group('status')
        for m in operational_status.finditer(check.stderr)])

    if wait:
        while not (
                all(m.group('status') == wait_for
                    for m in allocation_status.finditer(check.stderr))
                or
                all(m.group('status') == wait_for
                    for m in operational_status.finditer(check.stderr))
        ):
            print([m.group('status')
                for m in allocation_status.finditer(check.stderr)])
            print([m.group('status')
                for m in operational_status.finditer(check.stderr)])

            time.sleep(10)
            check = local(checkcmd, capture=True)

    regex = r'component_id=\\\"(?P<urn>.*?)\\\"'
    matches = re.finditer(regex, check.stderr, re.MULTILINE)
    hosts = [x.group('urn').split('+')[-1] for x in matches]
    hosts = ['root@' + x if x.startswith('tplink') else x for x in hosts]
    return hosts


@task(default=True)
def set_hosts(slice=None):
    if slice is not None:
        hosts = status(slice=slice, wait=True)
    else:
        hosts = status(wait=True)
    print(hosts)
    with settings(host_string=hosts[0]):
        try:
            run('ls')
        except fabric.exceptions.NetworkError:
            env.gateway = 'proxyuser@api.twist.tu-berlin.de:2222'
    env.hosts = hosts
    env.shell = '/bin/sh -c'


@task()
@parallel()
def install():
    sudo('apt install -yq'
        + ' wpasupplicant'
        + ' tcpdump'
        + ' python-setuptools'
        + ' python-pip'
         )
    sudo('pip install pyric')
    sudo('iw reg set DE')


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
    execute(status, wait=True, wait_for='geni_notready')
    local('omni performoperationalaction {args} {slice} geni_start'.format(
        args=args,
        slice=slice))

    execute(status, wait=True)


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
