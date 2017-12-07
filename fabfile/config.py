from fabric.api import *
from fabric.contrib.files import append
from fabric.contrib.files import contains


@task
@parallel
def install_openwrt():
    user = env.user
    with settings(user='root'):
        run('opkg update')
        run('opkg install '
            + ' tcpdump'
            + ' python-setuptools'
            + ' python-pip'
            + ' iperf'
            + ' openssh-sftp-server'
            + ' procps-pkill'
            + ' netperf'
            + ' procps'
            + ' procps-watch'
            + ' shadow-useradd'
            + ' sudo'
            )
        run('mkdir -p /home/')
        with settings(warn_only=True):
            run('useradd -s /bin/ash -m {}'.format(user))
        run('mkdir -p /home/{}/.ssh'.format(user))
        run('cp /etc/dropbear/authorized_keys /home/{}/.ssh/'.format(user))
        run('chown -R {u} /home/{u}'.format(u=user))
        if not contains('/etc/sudoers', 'Defaults env_keep += "HOME"'):
            append('/etc/sudoers', 'Defaults env_keep += "HOME"')
            append('/etc/sudoers', '%{} ALL=(ALL) NOPASSWD:ALL'.format(user))


@task
def remote():
    'Set config for remote work'
    env.gateway = 'proxyuser@api.twist.tu-berlin.de:2222'
