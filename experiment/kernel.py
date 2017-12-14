
from collections import namedtuple
from fabric import Connection

Kernel = namedtuple('Kernel', 'version release')


def kernels(ctx: Connection):
    """returns sorted list of installed kernels

    """
    result = ctx.run('ls /boot/vmlinuz*', hide=True)
    klist = []
    for release in result.stdout.split('\n'):
        release = release.replace('/boot/vmlinuz-', '')
        version = release.split('-')[0]
        if version:
            klist.append(Kernel(version, release))

    def version_key(x: Kernel):
        v = x.version.split('.')
        return int(v[0]), int(v[1]), int(v[2])

    return sorted(klist, key=version_key)


def switch(ctx: Connection, release: str):
    """Reboot node using kernel `release`

    """
    result = ctx.run('ls /boot/vmlinuz*', hide=True)
    if release not in result.stdout:
        raise ValueError('Kernel {release} not found')
    ctx.sudo('mv /vmlinuz /vmlinuz.old')
    ctx.sudo('mv /initrd.img /initrd.img.old')
    ctx.sudo(f'ln -fs boot/vmlinuz-{release} /vmlinuz')
    ctx.sudo(f'ln -fs boot/initrd.img-{release} /initrd.img')

    ctx.sudo('reboot', hide=True)
