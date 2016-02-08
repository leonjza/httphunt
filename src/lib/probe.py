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

import traceback

import click
import dataset
from bs4 import BeautifulSoup
from urllib3 import PoolManager, Timeout, exceptions, disable_warnings
import sqlalchemy

db = dataset.connect('sqlite:///httphunt.db')
session_data = db['httphunt_data']
session_headers = db['httphunt_headers']
session_links = db['httphunt_links']

disable_warnings()
http = PoolManager()


def scan_url(verbose, name, expire, override, url):
    """ Probe a URL. This is the worker function used by multiprocessing """

    try:

        if session_data.find_one(session=name, url=url):
            if not override:
                if verbose:
                    click.echo(click.style(
                        '[*] {url} has already been scanned'.format(url=url), fg='yellow'))
                return 'exists'
            else:
                if verbose:
                    click.echo(click.style(
                        '[*] Rescanning existing entry for {url}'.format(url=url), fg='green'))

        try:

            if verbose:
                click.echo('[*] Probing URL: {url}'.format(url=url))
            response = http.request('GET', url, timeout=Timeout(total=float(expire)))

        # AttributeError is for some crazy low level sockets thingy thing
        except (exceptions.MaxRetryError, exceptions.SSLError, AttributeError) as e:
            session_data.insert(dict(session=name, url=url, last_error=str(e.message)))

            if verbose:
                click.echo(
                    click.style('[*] An error occured on URL: {url}'.format(url=url), fg='red'))
            return 'error'

        soup = BeautifulSoup(response.data, 'html.parser')

        if verbose:
            click.echo(click.style(
                '[*] Saving response from {url} that had HTTP code {code}'.format(
                    url=url, code=response.status), fg='green'))

        session_data.insert(dict(
            session=name,
            url=url,
            page_title=soup.title.string if soup.title else None,
            status_code=response.status))

        if verbose:
            click.echo(click.style('[*] Saving {count} response headers for {url}'.format(
                count=len(dict(response.headers)), url=url), fg='green'))

        for k, v in response.headers.iteritems():
            session_headers.insert(dict(session=name, url=url, name=k, value=v))

        if verbose:
            click.echo(click.style('[*] Saving {count} HTML links for {url}'.format(
                count=len(soup.find_all('a')), url=url), fg='green'))

        for link in soup.find_all('a'):
            session_links.insert(dict(session=name, url=url, link=link.get('href')))

    except sqlalchemy.exc.OperationalError as e:
        click.echo(click.style(
            '[*] A database error occured: {error}'.format(error=e.message), fg='red'))

    except Exception, e:
        traceback.print_exc()
        raise e

    return 'done'
