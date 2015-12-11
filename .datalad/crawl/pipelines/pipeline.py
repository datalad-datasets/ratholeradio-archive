"""
Pipeline to fetch/update ratholeradio shows
"""
from __future__ import print_function

from datalad.crawler.nodes.annex import Annexificator
from datalad.crawler.nodes.crawl_url import crawl_url
from datalad.crawler.nodes.matches import a_href_match, css_match

from logging import getLogger
lgr = getLogger('datalad.custom.ratholeradio')

def process_episode(data):
    print("URL: {url}".format(**data))
    import pdb; pdb.set_trace()
    i = 1
#    yield data

def pipeline():
    lgr.info("Creating a pipeline for the ratholeradio")
    annex = Annexificator(
        create=False,  # must be already initialized etc
        options=["-c", "annex.largefiles=exclude=*.txt and exclude=*.cue"])

    return [
        crawl_url("http://ratholeradio.org",
                  matchers=[
#                      a_href_match('.*/page/[0-9]+'),
                  ]),
        a_href_match(".*/(?P<year>2[0-9]{3})/(?P<month>[0-9]{1,2})/ep(?P<episode>[0-9]+)/?$"),
        crawl_url(),
        # a_href_match(".*/RR.*\.(ogg|mp3)"),  # then would be one per each file
        css_match('div#page .entry',
                  xpaths={
                      'items': '//p',
                      'links': '//a',
                  },
                  allow_multiple=True),
        process_episode
    ]
