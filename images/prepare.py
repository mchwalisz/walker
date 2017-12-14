#!/usr/bin/env python
import os
import pathlib
import jinja2
import yaml
import sys
import tempfile
import invoke
import click
import awss3 as cloudstorage

BASE_PATH = pathlib.Path(__file__).absolute().parents[1]


def __build(diskimage, release, kernel):

    print(f'Creating "{diskimage}"..')

    sources_tmpl = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                str(pathlib.Path(__file__).parents[0]))).get_template(
                    'sources.list.jn2')

    sources_rendered = sources_tmpl.render({'release': release})

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as outfile:
        outfile.write(sources_rendered)
        sources_filename = outfile.name

    print(f'sources.list rendered to {sources_filename}')

    cmd = (
            "sudo -E bash -c '"
            "disk-image-create ubuntu-squashfs twist mainline-kernel"
            f" -t tgz -o {diskimage}'"
          )
    try:
        invoke.run(cmd,
                   env={
                        'DIB_KERNEL_VERSIONS': ','.join(kernel),
                        'DIB_APT_SOURCES': sources_filename,
                        'DIB_RELEASE': release,
                        'ELEMENTS_PATH': pathlib.Path(__file__)
                        .absolute().parents[0] / 'add_elements'
                       })
    finally:
        os.unlink(sources_filename)

    print(f'Done creating "{diskimage}"')


def __upload(diskimage):
    print(f'Uploading {diskimage} to cloud storage..')
    url = cloudstorage.upload(diskimage, 'static')
    print(f'Uploaded {diskimage} to cloud storage. URL: {url}')
    return(url)


def __render_rspec(url):
    with open(BASE_PATH / 'node_selection' / 'hosts', 'r') as stream:
        node_spec = yaml.load(stream)

    nodes = list()
    for node_type in node_spec:
        for node_name in node_spec[node_type]['hosts']:
            node = {
                    'name': node_name,
                    'type': node_type,
                    'disk_image': url
                    }
            nodes.append(node)

    rspec = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                str(BASE_PATH / 'node_selection'))).get_template('rspec.jn2')

    output = rspec.render({'nodes': nodes})

    rspec_path = BASE_PATH / 'node_selection' / 'rendered.rspec'
    with open(rspec_path, 'w') as f:
        f.write(output)

    print(f'Rspec written to {rspec_path}')


@click.group(invoke_without_command=True)
@click.option('--diskimage', '-d', default='image.tgz',
              help='Filename for diskimage')
@click.option('--release', '-r', default='artful', help='Ubuntu release codename')
@click.option('--kernel', '-k', multiple=True, default='4.14.5',
              help='Version number of mainline kernel to bake into image')
@click.pass_context
def cli(ctx, diskimage, release, kernel):
    if ctx.invoked_subcommand is None:
        __build(diskimage, release, kernel)
        url = __upload(diskimage)
        __render_rspec(url)
    else:
        ctx.obj['diskimage'] = diskimage
        ctx.obj['release'] = release
        ctx.obj['kernel'] = kernel


@cli.command()
@click.pass_context
def build(ctx):
    __build(ctx.obj['diskimage'], ctx.obj['release'], ctx.obj['kernel'])


@cli.command()
@click.pass_context
def upload(ctx):
    __upload(ctx.obj['diskimage'])


@cli.command()
@click.option('--url',
              help='diskimage URL to bake into rspec')
def render_rspec(url):
    __render_rspec(url)


if __name__ == '__main__':
    cli(obj={})
