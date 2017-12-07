#!/usr/bin/env python

import click
from fabric import Connection
from fabric import SerialGroup
import wifi


@click.group(
    context_settings=dict(help_option_names=['-h', '--help']))
@click.option('-v', '--verbose', count=True)
@click.version_option('v0.1.0')
def cli(verbose):
    # click.echo('Verbosity: %s' % verbose)
    pass


@cli.command(short_help="Run experiment")
def run():
    hosts = ['nuc4', 'nuc10', 'nuc12']
    grp = SerialGroup(*hosts)
    ap = Connection(hosts[0])
    grp.run('uname -s -n -r')
    wifi.info(grp)
    # wifi.reload(ap)
    wifi.create_ap(ap, phy='03:00', ssid='exp1', channel=1)
    wifi.connect(Connection(hosts[1]), phy='03:00', ssid='exp1')


if __name__ == '__main__':
    cli()
