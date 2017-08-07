#!/usr/bin/env python

from time import sleep
import click
from fabric.api import *
import fabfile as tasks

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True)
@click.version_option('v0.1.0')
def cli(verbose):
    # click.echo('Verbosity: %s' % verbose)
    pass


@cli.command('speed_test', short_help='iperf between two Wi-Fi nodes')
@click.option('--ap', '-a', default='tplink01', help='Hostname for AP')
@click.option('--sta', '-s', default='nuc5', help='Hostname for STA')
@click.option('--ssid', default='TSCH', help='Network name')
@click.option('--channel', default=11, type=int, help='Network name')
def speed_test(ap, sta, ssid, channel):
    """Measures throughput between AP and STA with iperf"""
    if ap.startswith('tplink'):
        ap = 'root@' + ap
    if sta.startswith('tplink'):
        sta = 'root@' + sta
    apip = '10.100.1.1'
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
    sleep(2)
    result = execute(tasks.iperf,
        dest=apip, hosts=[sta])
    print(result)


if __name__ == '__main__':
    cli()
