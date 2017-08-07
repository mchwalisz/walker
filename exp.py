#!/usr/bin/env python

from time import sleep
import click
from fabric.api import *
import fabfile as tasks
from datetime import datetime

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True)
@click.version_option('v0.1.0')
def cli(verbose):
    # click.echo('Verbosity: %s' % verbose)
    pass


@cli.command('speed_test', short_help='iperf between two Wi-Fi nodes')
@click.option('--ap', '-a',
    default='tplink01', show_default=True,
    help='Hostname for AP')
@click.option('--sta', '-s',
    default='nuc5', show_default=True,
    help='Hostname for STA')
@click.option('--ssid',
    default='TSCH', show_default=True,
    help='Network name')
@click.option('--channel',
    default=11, type=int, show_default=True,
    help='Network name')
@click.option('--duration', '-t',
    default=20, type=int, show_default=True,
    help='Iperf duration')
@click.option('--setup/--no-setup',
    default=True, show_default=True,
    help='Setup networks')
@click.option('--teardown/--no-teardown',
    default=False, show_default=True,
    help='Tear down networks')
def speed_test(ap, sta, ssid, channel, duration, setup, teardown):
    """Measures throughput between AP and STA with iperf"""
    if ap.startswith('tplink'):
        ap = 'root@' + ap
    if sta.startswith('tplink'):
        sta = 'root@' + sta
    apip = '10.100.1.1'

    if setup:
        execute(tasks.wifi.ifaces_clean, hosts=[ap, sta])
        # phys = execute(wifi.phys_get, hosts=[ap, sta])
        execute(tasks.wifi.create_ap,
            channel=channel,
            hw_mode='g' if channel < 13 else 'n',
            ssid=ssid,
            phy='phy0',
            ip=apip,
            hosts=[ap])
        execute(tasks.wifi.connect,
            phy='phy0',
            ssid=ssid,
            hosts=[sta])

    execute(tasks.iperf, server=True, hosts=[ap])
    result = execute(
        tasks.iperf,
        duration=duration,
        dest=apip, hosts=[sta])

    result[sta].to_csv(
        'data/speed_test_{}.csv'.format(
            datetime.now().isoformat()))
    print(result)

    if teardown:
        execute(tasks.iperf, clean=True, hosts=[ap, sta])
        execute(tasks.wifi.ifaces_clean, hosts=[ap, sta])


if __name__ == '__main__':
    cli()
