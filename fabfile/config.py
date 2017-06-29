import time
import datetime as dt
import fabric
from fabric.api import *
import re


@task()
def status(slice='wifi-channel', wait=False):
    args = '-V3 -a twist'
    checkcmd = 'omni describe {args} {slice}'.format(
        args=args,
        slice=slice)

    check = local(checkcmd, capture=True)

    if wait:
        while check.stderr.find('geni_ready') == -1:
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
def packages():
    sudo('apt install -yq wpasupplicant')


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
            print(green('Resources ready'))
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
