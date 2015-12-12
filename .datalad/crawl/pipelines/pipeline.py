"""
Pipeline to fetch/update ratholeradio shows
"""
from __future__ import print_function
import re

from datalad.utils import updated
from datalad.crawler.nodes.annex import Annexificator
from datalad.crawler.nodes.crawl_url import crawl_url
from datalad.crawler.nodes.matches import a_href_match, css_match

from logging import getLogger
lgr = getLogger('datalad.custom.ratholeradio')

def process_episode(data):
    # create cue out of
    lgr.info("Processing URL: {url}".format(**data))
    items = []
    # some times \u2014 was used to split up pairs
    for item in data['items']:
        items.extend(item.split(u'\u2014'))

    tracks = []
    for item in items:
        fields = [re.sub('<.*?>', '', x).strip()  # strip all HTML goodness
                  for x in item.split(u'\u2013')]
        fields = filter(bool, fields)  # remove empty
        if len(fields) > 0:
            if len(fields) == 4:
                time, artist, title, license = fields
            elif len(fields) == 3:
                time, artist, title = fields
                license = None
            else:
                lgr.warning("Got %d fields: %s" % (len(fields), str(fields)))
                continue
            # Let's just write that time
            try:
                _ = map(int, time.split(':', 1))
            except:
                # must be smth else but time
                continue
        else:
            continue
        tracks.append({'time': time, 'artist': artist, 'title': title, 'license': license})

    if tracks and tracks[0]['time'].lstrip('0') == ':00':
        # offset first track by 10 sec to account for Dan's overlay
        tracks[0]['time'] = '00:10'

    if tracks:
        mp3_file = data['mp3'][0].split('/')[-1]
        assert(mp3_file.endswith('.mp3'))
        lgr.info("Harvested %d tracks for the %s" % (len(tracks), mp3_file))
        for ext in ('mp3', 'ogg'):
            ext_file = mp3_file.replace('.mp3', '.' + ext)
            cue_file = mp3_file.replace('.mp3', '_%s.cue' % ext)
            lgr.debug("Composing %s", cue_file)
            data_ = data.copy()
            data_['EXT'] = ext.upper()
            data_['ext_file'] = ext_file
            with open(cue_file, 'w') as f:
                f.write(u"""REM GENRE "Eclectic music from around the web"
REM DATE "{year}"
PERFORMER "Dan Lynch"
TITLE "Episode {episode}"
FILE "{ext_file}" {EXT}
TRACK 01 AUDIO
 TITLE "Introduction"
 PERFORMER "Dan Lynch"
 INDEX 01 00:00:00
""".format(**data_).encode('utf-8'))
                for i, track in enumerate(tracks, 2):
                    track_entry = u"""\
TRACK {index:02d} AUDIO
 TITLE "{title}"
 PERFORMER "{artist}"
 INDEX 01 {time}:00
""".format(index=i, **track)
                    f.write(track_entry.encode('utf-8'))
            out = updated(data, dict(filename=cue_file))
            out.pop('url')  # URL is no longer associated with this file
            yield out


def pipeline():
    lgr.info("Creating a pipeline for the ratholeradio")
    annex = Annexificator(
        create=False,  # must be already initialized etc
        mode='relaxed',
        options=["-c", "annex.largefiles=exclude=*.cue"])

    return [
        crawl_url("http://ratholeradio.org",
                  matchers=[
#                      a_href_match('.*/page/[0-9]+'),
                  ]),
        a_href_match(".*/(?P<year>2[0-9]{3})/(?P<month>[0-9]{1,2})/ep(?P<episode>[0-9]+)/?$"),
        crawl_url(),
        [
            css_match('div#page .entry',
                      xpaths={'items': '//p',
                              'mp3': "//a[contains(@href, '.mp3')]//@href"},
                      allow_multiple=True),
            process_episode,
            annex
        ],
        [
            a_href_match('.*/RR.*\.(ogg|mp3)'),
            annex
        ]
    ]
