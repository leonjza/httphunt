#!/usr/bin/python

# The MIT License (MIT)
#
# Copyright (c) 2016 Leon Jacobs
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import multiprocessing
import uuid
from collections import Counter
from functools import partial

import click
import dataset
from lib import util, probe, reporting
from netaddr import IPNetwork
from tabulate import tabulate

version = '0.1'

db = dataset.connect('sqlite:///httphunt.db')
session_name = db['httphunt_sessions']
session_data = db['httphunt_data']
session_headers = db['httphunt_headers']
session_links = db['httphunt_links']

default_target_ports = '80,443s'


class State(object):
    """ A State for common options """

    def __init__(self):
        self.verbosity = 0


pass_state = click.make_pass_decorator(State, ensure=True)


def verbosity_option(f):
    """ The global verbosity option """

    def callback(ctx, _, value):
        state = ctx.ensure_object(State)
        state.verbosity = value
        return value

    return click.option('-v', '--verbose', count=True, expose_value=False, help='Enables verbosity',
                        callback=callback)(f)


def common_options(f):
    """ A decorator for the commtion options """

    f = verbosity_option(f)
    return f


@click.group()
def cli():
    """
        httphunt

        A HTTP Service Hunter.
    """
    util.prepare_database()

    click.echo(' __ __  ______  ______  ____   __ __  __ __  ____   ______ \n' +
               '|  |  ||      ||      ||    \ |  |  ||  |  ||    \ |      |\n' +
               '|  |  ||      ||      ||  o  )|  |  ||  |  ||  _  ||      |\n' +
               '|  _  ||_|  |_||_|  |_||   _/ |  _  ||  |  ||  |  ||_|  |_|\n' +
               '|  |  |  |  |    |  |  |  |   |  |  ||  :  ||  |  |  |  |  \n' +
               '|  |  |  |  |    |  |  |  |   |  |  ||     ||  |  |  |  |  \n' +
               '|__|__|  |__|    |__|  |__|   |__|__| \__,_||__|__|  |__|  \n' +
               '                               v{version} @leonjza         \n'.format(version=version))


@cli.command()
@common_options
@pass_state
@click.option('--name', '-n', default=None, help='A name for this session')
@click.option('--cidr', '-c', help='An IP Range in CIDR format', required=True)
@click.option('--ports', '-p', default=default_target_ports, help='A comma seperated list of ports to scan')
@click.option('--timeout', '-t', default=5.0, help='Time in seconds to wait for a response')
@click.option('--override', '-O', default=False, is_flag=True, help='Override existing entries for this session')
@click.option('--threads', '-T', default=5, help='# of simultaneous scan threads')
def scan(state, name, cidr, ports, timeout, override, threads):
    """
        Scan a CIDR

        Specify a CIDR (192.168.0/24) to scan. Ports with a trailing
        's' will be treated as HTTPs.

        EXAMPLES:

            python httphunt.py scan --cidr 192.168.0/24


            python httphunt.py scan --cidr 192.168.0/24 --name test1 --ports 80,443s,8443s
    """

    if not name:
        name = str(uuid.uuid4())

    target_network = IPNetwork(cidr)
    target_ports = [x for x in ports.split(',') if x]
    if not target_ports:
        target_ports = [x for x in default_target_ports.split(',')]

    if not session_name.find_one(name=name):
        click.echo(click.style(
            '[*] Recording new session name: {name}'.format(name=name), fg='green'))
        session_name.insert(
            dict(name=name, network=str(target_network), ports=','.join(target_ports)))
    else:
        click.echo(click.style(
            '[*] Using existing session name: {name}'.format(name=name), fg='yellow'))

    click.echo(click.style('[*] Specified CIDR has {hosts} hosts to scan on {ports} ports'.format(
        hosts=target_network.size, ports=len(target_ports)), fg='white', bold=True))

    # Work on the hosts in the CIDR using multiprocessing.
    # Lots of magic-fu partial functions and funky stuff
    # going on here.
    func = partial(probe.scan_url, state.verbosity, name, timeout, override)
    pool = multiprocessing.Pool(processes=threads, maxtasksperchild=1)
    jobs = pool.imap_unordered(
        func, util.generate_targets(target_network, target_ports), chunksize=1)

    # Iterate through all the results. Jobs without a timeout
    # results in ^C being borked for some reason.
    results = []
    try:
        if not state.verbosity:
            with click.progressbar(show_pos=True, show_percent=True,
                                   length=target_network.size * len(target_ports)) as bar:
                while True:
                    result = jobs.next(timeout=99999999999)
                    results.append(result)
                    bar.update(1)

        else:
            while True:
                result = jobs.next(timeout=99999999999)
                results.append(result)

    except StopIteration:
        pass

    # Clean up the progressbar if needed
    if not state.verbosity:
        bar.finish()

    click.echo(click.style(
        '[*] Scan complete for session: {session}'.format(session=name), fg='green'))
    click.echo('[*] Scan Summary')
    click.echo(tabulate(Counter(results).items()))


@cli.group()
def report():
    """
        Generate text reports
    """
    pass


@report.command()
@common_options
def available():
    """
        Show Available Reports
    """

    reporting.all_reports()


@report.command()
@common_options
@click.option('--name', '-n', help='The name of the session to show', required=True)
@click.option('--full', '-f', default=False, is_flag=True, help='Show full report with errors')
def session(name, full):
    """
        Show a specific report
    """

    if not full:
        reporting.session_with_errors(name)
    else:
        reporting.session(name)


@report.command()
@common_options
@click.option('--name', '-n', help='The name of the session to show', required=True)
@click.option('--url', '-u', help='A specific URLs info to show')
def data(name, url):
    """
        Show a specific reports data
    """

    if url:
        reporting.session_data_by_name_url(name, url)
    else:
        reporting.session_data_by_name(name)


@report.command()
@common_options
@click.option('--name', '-n', help='The name of the session', required=True)
def html(name):
    """ Generate HTML Reports """

    reporting.html_session_report(name)


if __name__ == '__main__':
    cli()
