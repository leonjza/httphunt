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

import click
import dataset
import os
from jinja2 import Environment, FileSystemLoader
from tabulate import tabulate

db = dataset.connect('sqlite:///httphunt.db')
session_name = db['httphunt_sessions']
session_data = db['httphunt_data']
session_headers = db['httphunt_headers']
session_links = db['httphunt_links']

template_environment = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(
        os.path.dirname(os.path.abspath(__file__)) + '/../', 'templates')),
    trim_blocks=False)


def all_reports():
    click.echo(click.style('[*] All Available Reports', fg='green'))
    click.echo(tabulate(session_name.all(), headers='keys'))


def session(name):
    click.echo(tabulate(session_data.find(session=name), headers='keys'))


def session_with_errors(name):
    result = db.query(
        'SELECT * FROM `httphunt_data` WHERE `session` = "{session}" AND status_code IS NOT NULL'.format(
            session=name))
    click.echo(tabulate(result, headers='keys'))


def session_data_by_name(name):
    click.echo('\n[*] Per URL Information'.format(name=name))
    for url in session_data.find(session=name):
        if url['status_code'] is None:
            continue

        headers = session_headers.find(session=name, url=url['url'])
        if not headers:
            continue

        click.echo(click.style('\n[*] Response Headers for URL {url}\n'.format(url=url['url']), fg='green'))
        click.echo(tabulate(headers, headers='keys'))

        links = session_links.find(session=name, url=url['url'])
        if not links:
            continue

        click.echo(click.style('\n[*] HTML Links for URL {url}\n'.format(url=url['url']), fg='green'))
        click.echo(tabulate(links, headers='keys'))


def session_data_by_name_url(name, url):
    headers = session_headers.find(session=name, url=url)
    if headers:
        click.echo(click.style('\n[*] Response Headers for URL {url}\n'.format(url=url), fg='green'))
        click.echo(tabulate(headers, headers='keys'))

    links = session_links.find(session=name, url=url)
    if links:
        click.echo(click.style('\n[*] HTML Links for URL {url}\n'.format(url=url), fg='green'))
        click.echo(tabulate(links, headers='keys'))


def html_session_report(name):
    html = template_environment.get_template('session.html').render(
        {
            'summary': session_name.find_one(name=name),
            'session': db.query(
                'SELECT * FROM `httphunt_data` WHERE `session` = "{session}" AND status_code IS NOT NULL'.format(
                    session=name)),
            'headers': session_headers.find(session=name),
            'links': session_links.find(session=name)
        }
    )

    with open('session_report.html', 'w') as f:
        f.write(html.encode('utf8'))

    click.launch('file://session_report.html')
