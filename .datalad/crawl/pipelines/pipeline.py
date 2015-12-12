# -*- coding: utf-8 -*-
"""
Pipeline to fetch/update ratholeradio shows
"""
from __future__ import print_function
import re
from os.path import join as opj, basename

from datalad.utils import updated
from datalad.crawler.nodes.annex import Annexificator
from datalad.crawler.nodes.crawl_url import crawl_url
from datalad.crawler.nodes.misc import sub
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
            fields = [x.strip('\n\t- ') for x in fields]
            if len(fields) >= 4:
                time, artist, title, license = fields[:4]
            elif len(fields) == 3:
                time, artist, title = fields
                license = None
            elif len(fields) == 2:
                # e.g. in ep 25 -- list of songs Dan performed
                time, title = fields
                if "Originally by" in title:
                    # Let's do it nice
                    reg = re.match("\s*(?P<title>.*?)\s*\(Originally by\s*(?P<orig_author>.+)\)\s*", title)
                    matches = reg.groupdict()
                    artist = "Dan Lynch (originally by {orig_author})".format(**matches)
                    title = matches['title']
                license = None
            else:
                lgr.debug("Got %d fields: %s" % (len(fields), str(fields)))
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
        # offset first track by 15 sec to account for Dan's overlay
        tracks[0]['time'] = '00:15'

    lgr.info("Harvested %d tracks" % (len(tracks)))
    # Some episodes lacked time information about tracks or just few (as in 85)
    if len(tracks) < 6 and data['episode'] not in {'100', '64', '85'}:
        # something must have went wrong
        import pdb; pdb.set_trace()

    for ext in ('mp3', 'ogg'):
        ext_file = data[ext].split('/')[-1]
        # early episodes seemed to have another prefix -- let's unify
        # and also year as two digit later became 4 digit year.
        # Well -- in data we should have everything but the date, but actually
        # release month/date some times was different from the file date. So let's
        # reparse the filename again
        reg = re.match(
            "[A-Za-z_]+"
            "((?P<episode>[0-9]+)[-_])?"
            "(?P<date>[0-9]{1,2})[-_]"
            "(?P<month>[0-9]{1,2})[-_]"
            "(?P<year>[0-9]{2,4})\.(?P<ext>(mp3|ogg))", ext_file)

        if not reg:
            raise ValueError("Could not parse %s" % ext_file)
        parts = reg.groupdict()
        if not 'episode' in parts:
            parts['episode'] = data['episode']
        if len(parts['year']) == 2:
            parts['year'] = '20' + parts['year']
        # reconstitute the filename
        ext_file = "RR{episode:>03s}_{date:>02s}_{month:>02s}_{year}.{ext}".format(**parts)

        ext_file = opj(ext, ext_file)
        # instruct to download/annex the file itself
        yield {
            'url': data[ext],
            'filename': ext_file
        }

        if tracks:
            cue_file = ext_file[:-4] + '.cue'
            lgr.debug("Composing %s", cue_file)
            data_ = data.copy()
            data_['EXT'] = ext.upper()
            data_['ext_file'] = basename(ext_file)
            with open(cue_file, 'w') as f:
                f.write(u"""REM GENRE "Eclectic music from around the web"
REM DATE "{year}"
PERFORMER "Dan Lynch"
ALBUMARTIST "Dan Lynch"
TITLE "Rathole Radio ep. {episode}"
FILE "{ext_file}" {EXT}
TRACK 01 AUDIO
 TITLE "http://ratholeradio.org Introduction"
 PERFORMER "Dan Lynch"
 INDEX 01 00:00:00
 COMMENT "http://ratholeradio.org"
""".format(**data_).encode('utf-8'))

                for i, track in enumerate(tracks, 2):
                    track_entry = u"""\
TRACK {index:02d} AUDIO
 TITLE "{title}"
 PERFORMER "{artist}"
 INDEX 01 {time}:00
""".format(index=i, **track)
                    if track['license']:
                        track_entry += u""" COMMENT "{license}"\n""".format(**track)
                    f.write(track_entry.encode('utf-8'))
            # we just need to annex the cue_file, no other information to be passed
            yield {
                'filename': cue_file
            }


def pipeline():
    lgr.info("Creating a pipeline for the ratholeradio.org podcasts")
    annex = Annexificator(
        create=False,  # must be already initialized etc
        mode='relaxed',
        allow_dirty=True,  # XXX for now
        options=["-c", "annex.largefiles=exclude=*.cue"])

    return [
        [
            crawl_url("http://ratholeradio.org",
                      matchers=[
                          a_href_match('.*/page/[0-9]+'),
                      ]),
            a_href_match(".*/(?P<year>2[0-9]{3})/(?P<month>[0-9]{1,2})/ep(?P<episode>[0-9]+)/?$"),
            crawl_url(),
            [
                sub({'response': {
                        '</?strong>': '',  # ep 7? used also lots of strongs
                        '</?span[^>]*>': '',  # ep 74 used spans too extensively
                        # in raw HTML at this point
                        r'(\d{2}:\d{2}) &#8212;': r'\1 &#8211;', # ep 7 used long dash which later was used to bind pairs
                        }
                    }),
                # Items which might contain tracks information
                css_match('div#page .entry',
                          xpaths={'items': u"//*[contains(text(), '–')]"},
                          allow_multiple=True),
                # URLs to download mp3/ogg.
                css_match('div#page .entry',
                          xpaths={'mp3': "//a[re:test(@href, '.*\.mp3$')]//@href",
                                  'ogg': "//a[re:test(@href, '.*\.ogg$')]//@href",
                                  }),
                process_episode,
                annex
            ],
        ],
        annex.finalize  # isn't triggered atm -- BUG
    ]
