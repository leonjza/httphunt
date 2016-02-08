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

from urlparse import urlparse

import click
import dataset

db = dataset.connect('sqlite:///httphunt.db')
session_name = db['httphunt_sessions']
session_data = db['httphunt_data']
session_headers = db['httphunt_headers']
session_links = db['httphunt_links']


def prepare_database():
    """ Ensure the database is ready for use """

    if len(session_name.columns) is not 4:
        click.echo(click.style('[*] Initializing session table', fg='green'))
        session_name.insert(dict(name=None, network=None, ports=None))
        session_name.delete(name=None)

    if len(session_data.columns) is not 6:
        click.echo(click.style('[*] Initializing session data table', fg='green'))
        session_data.insert(dict(session=None, url=None, page_title=None, status_code=None, last_error=None))
        session_data.delete(session=None)

    if len(session_headers.columns) is not 5:
        click.echo(click.style('[*] Initializing session headers table', fg='green'))
        session_headers.insert(dict(session=None, url=None, name=None, value=None))
        session_headers.delete(session=None)

    if len(session_links.columns) is not 4:
        click.echo(click.style('[*] Initializing session links table', fg='green'))
        session_links.insert(dict(session=None, url=None, link=None))
        session_links.delete(session=None)


def generate_targets(network, ports):
    """ A generator for compiled URLs"""

    return [(urlparse(x).geturl()) for x in
            [''.join([
                'https://' if 's' in port else 'http://',
                str(ip), ':',
                str(port).replace('s', '')
            ]) for ip in network.iter_hosts() for port in ports]]
