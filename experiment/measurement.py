
from fabric import Connection


def iperf_server(
        cnx: Connection):
    """Starts iperf3 server in background.

    Args:
        cnx (Connection): Fabric connection context
    """
    cnx.run('pkill iperf3', warn=True, hide=True)
    cnx.run('iperf3 --daemon --json --server')


def iperf_client(
        cnx: Connection,
        ip: str = '10.1.1.1',
        traffic: str = 'udp',
        duration: int = 20,
        extra_args: str = ''):
    """Starts iperf3 client

    Args:
        cnx (Connection): Fabric connection context
        ip (str): Destination IP
        traffic (str): Traffic type (UDP or TCP)
        duration (int): Test duration (in seconds)
        extra_args (str): Additional iperf3 arguments
    """
    cnx.run('pkill iperf3', warn=True, hide=True)

    if traffic.lower() == 'udp':
        conf = '-u -b 100m'
    else:
        conf = ''
    result = cnx.run(
        f'iperf3 --client {ip} -t {duration} --json {conf} {extra_args}',
        hide=True,
        warn=True)
    return result
