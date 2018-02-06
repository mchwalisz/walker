import logging
import multiprocessing
import socket
import time

from ansible.plugins.action import ActionBase
from contextlib import closing
from fabric import Connection


logger = logging.getLogger('bootos')
logger.setLevel(logging.DEBUG)


def check_port(host, port):
    logger.debug('checking ssh port for {}:{}'.format(host, port))
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex((host, int(port))) == 0:
            return True
        else:
            logger.debug('ssh port not open: {}@{}'.format(host, port))
            return False


def get_status(host, user):
    host_string = '{:s}@{:s}'.format(user, host)
    logger.debug('get status for {}'.format(host_string))
    res = run_cmd(host, user, 'grep -Fxq "True" /etc/baseosflag')
    if(res == 0):
        return 'base'
    else:
        return 'experiment'


def wait_for_host(host, user, timeout, delay=0):
    host_string = '{:s}@{:s}'.format(user, host)
    logger.debug("wait for host {}".format(host_string))
    time.sleep(delay)
    t_start = time.time()
    while time.time() < (t_start + timeout):
        try:
            res = run_cmd(host, user, '/bin/true')
            if(res == 0):
                logger.debug("success login to {}".format(host_string))
                return
        except Exception:
            logger.debug("failed login to {}".format(host_string))

        logger.debug('waiting {:.2f}s for {}'.format(
            t_start + timeout - time.time(), host_string))
        time.sleep(5)
    raise Exception


class FabricProcess(multiprocessing.Process):
    def __init__(self, user, host, cmd, privileged):
        super(FabricProcess, self).__init__()
        self.ctx = Connection('{:s}@{:s}'.format(user, host))
        self.operation = self.ctx.sudo if (
            user != 'root' and privileged) else self.ctx.run
        self.cmd = cmd
        self.return_code = multiprocessing.Value('i', -1)

    def run(self):
        res = self.operation(self.cmd, shell=False, hide=True, warn=True)
        self.ctx.close()
        self.return_code.value = res.return_code


def run_cmd(host, user, cmd, privileged=False):
    logger.debug("run cmd \"{}\" on {}@{}".format(
        cmd, user, host))

    port = 22
    command_timeout = 10

    if not check_port(host, port):
        raise Exception

    logger.debug("ssh port open on {}@{}".format(user, host))
    logger.debug("spawning fabric process..")

    fp = FabricProcess(user, host, cmd, privileged)
    fp.start()

    t_start = time.time()
    while time.time() < (t_start + command_timeout):
        if(fp.exitcode is not None):
            break
        time.sleep(1)

    if(fp.exitcode is None):
        fp.terminate()
        logger.debug("timeout run cmd \"{}\" on {}@{}".format(
            cmd, user, host))
        raise TimeoutError()

    logger.debug("passed run cmd \"{}\" on {}@{}. Exit code: {}".format(
        cmd, user, host, fp.return_code.value))
    return fp.return_code.value


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        args = self._task.args.copy()

        # key_filename = task_vars['ansible_ssh_private_key_file']
        # logger.debug("using private key from {:s}".format(key_filename))

        if 'experimentuser' not in args:
            args['experimentuser'] = 'ansible_user'

        if not args['reboot']:
            status = get_status(
                task_vars['ansible_host'], task_vars['ansible_user'])
            if(status == args['image']):
                result['changed'] = False
                return result

        if args['image'] == 'base':
            self.boot_base(
                task_vars['ansible_host'], task_vars['ansible_user'])
            result['changed'] = True

        elif args['image'] == 'experiment':
            res = self.boot_experiment(
                task_vars['ansible_host'],
                task_vars['ansible_user'],
                args['experimentuser'],
                args,
                task_vars)
            result.update(res)

        return result

    def boot_experiment(
            self, host, user, experimentuser, args, task_vars):
        logger.debug('boot {} to experiment'.format(host))

        status = get_status(host, user)
        if status != 'base':
            self.boot_base(host, user)

        logger.debug('run kexec on {}'.format(host))
        res = self._execute_module(
            module_args=args, task_vars=task_vars)

        wait_for_host(host, experimentuser, 240, delay=10)
        status = get_status(host, experimentuser)
        if status == 'experiment':
            return res
        else:
            raise Exception

    def boot_base(self, host, user):
        logger.debug('boot {} to base'.format(host))
        status = get_status(host, user)
        if status != 'base':
            ret = run_cmd(host, user, 'reboot', True)
            if(ret != 0):
                raise Exception

        wait_for_host(host, user, 240, delay=10)
        if get_status(host, user) == 'base':
            return
        else:
            raise Exception
