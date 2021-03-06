#!/usr/bin/env python2
'This is for the old data format.'

import datetime
import lxml.html, lxml.etree
import re
from unidecode import unidecode
import json

def listing_parse(rawtext):
    # There are more data in the comments!
    text_with_locations = rawtext.replace('<!--', '').replace('-->', '').replace('&nbsp;', ' ')
    unicodetext = unidecode(text_with_locations)
    html = lxml.html.fromstring(unicodetext)
    nodes = html.xpath('//table[@width="570" and @border="1" and @cellpadding="0" and @cellspacing="0" and @bordercolor="#ffffff" and @bgcolor="#efefef"]')
    if len(nodes) == 1:
        table = nodes[0]
    else:
        print nodes
        raise AssertionError('Not exactly one table')
    trs = table.xpath('tr')

    # Getting the cells
    thead = [td.text_content().strip() for td in trs.pop(0)]
    if len(thead) != _NCOL:
        _log(thead)
        _RRRaise(AssertionError('The table header does not have exactly %d cells.' % _NCOL))

    if thead != _COLNAMES:
        pairs = zip(thead, _COLNAMES)
        for a, b in pairs:
            _log(a, b), 'Match' if a == b else 'Differ'
        _RRRaise(AssertionError('The table header does not have the right names.'))

    # List of dictionaries of data
    data = []
    publicnotices = []
    drawings = []
    for tr in trs:
        if len(tr.xpath('td')) != _NCOL:
            _RRRaise(AssertionError('The table row does not have exactly %d cells.' % _NCOL))

        # As a dict
        row = dict(zip(thead, [td.text_content().strip() for td in tr.xpath('td')]))

        # Skip junk permit application numbers
        if row['PermitApplication No.'] in SKIP:
            continue

        # Clean up the permit application number
        try:
            row['PermitApplication No.'] = _clean_permit_application_number(row['PermitApplication No.'])
        except:
            print [row['PermitApplication No.']]
            raise

        # Dates
        row['Public Notice Date'] = _parsedate(row['Public Notice Date']).strftime('%Y-%m-%d')
        row['Expiration Date'] = _parsedate(row['Expiration Date']).strftime('%Y-%m-%d')

        # PDF download links
        del(row['View or Download'])
        pdfkeys = set(tr.xpath('td[position()=6]/descendant::a/text()'))
        if not pdfkeys.issubset({'Public Notice', 'Drawings'}):
            _log(pdfkeys)
            _RRRaise(AssertionError('The table row has unexpected hyperlinks.'))
        if len(pdfkeys) == 0:
            print(row)
            _RRRaise(AssertionError('No pdf hyperlinks found for permit %s.' % row['PermitApplication No.']))
        for key in ['Public Notice', 'Drawings']:
            nodes = tr.xpath('td/descendant::a[text()="%s"]/@href' % key)
            if len(nodes) == 0:
                continue
            elif len(nodes) == 1:
                row[key] = nodes[0]
            else:
                print row
                raise AssertionError('More than one %s node' % key)

            if row[key][:4] != 'pdf/':
                _RRRaise(AssertionError('The %s pdf link doesn\'t have the expected path.' % key))

        # Project manager contact information
        del(row['Project Manager'])
        pm = _onenode(tr, 'td[position()=8]')

        # Email address
        try:
            row['Project Manager Email'] = _onenode(pm, 'descendant::a/@href')
        except AssertionError:
            _log(row)
            raise

        if row['Project Manager Email'][:7] == 'mailto:':
            row['Project Manager Email'] = unicode(row['Project Manager Email'][7:])
        else:
            msg = 'This is a strange email link: <%s>' % row['Project Manager Email']
            _RRRaise(AssertionError(msg))

        # Name
        row['Project Manager Name'] = _onenode(pm, 'descendant::a').text_content().strip()

        # Phone number
        phone_match = re.match(_PHONE_NUMBER, pm.text_content())
        if phone_match:
            row['Project Manager Phone'] = phone_match.group(1)
        else:
            _log(row)
            msg = 'This is a strange phone number: %s' % pm.text_content()
            _RRRaise(AssertionError(msg))

        # Append to our big lists
        data.append(row)

    data2 = []
    for row in data:
        row2 = {new: row.get(old, None) for old, new in _KEYMAP}
        for k, v in row2.items():
            if type(v) in {lxml.etree._ElementStringResult, str}:
                row2[k] = unicode(v)
        row2['parish'] = _extract_parish(row2['location'])
        row2['status'] = 1
        for k in [
            'longitude', 'latitude', 'acreage',
            'CUP', 'WQC',
            'notes', 'flagged', 'type',
            'locationOfWork', 'characterOfWork',
            'reminderDate',
        ]:
            row2[k] = ''

        data2.append(row2)

    return data2

_KEYMAP = [
    ('Project Description','projectDescription'),
    ('Applicant','applicant'),
    ('PermitApplication No.','permitApplicationNumber'),
    ('Public Notice Date','publicNoticeDate'),
    ('Public Notice','publicNoticeUrl'),
    ('Location','location'),
    ('Drawings','drawingsUrl'),
    ('Expiration Date','expirationDate'),
    ('Project Manager Email', 'projectManagerEmail'),
    ('Project Manager Name','projectManagerName'),
    ('Project Manager Phone','projectManagerPhone'),
]
_PHONE_NUMBER = re.compile(r'[^0-9]*(\d{3}-\d{3}-\d{4})[^0-9]*')
_NCOL = 8
_COLNAMES = [
    'Project Description',
    'Applicant',
    'Public Notice Date',
    'Expiration Date',
    'PermitApplication No.',
    'View or Download',
    'Location',
    'Project Manager'
]

PERMIT_APPLICATION_NUMBER_REGEX = re.compile(r'^MV[KN]-[0-9]+-[0-9]+(?:-[A-Z]+)?$')
PERMIT_YEAR = re.compile(r'[12][901][789012][0-9]')

MANUAL_REPLACEMENTS = {
    'MVN 2009-3063 CO (ERRATUM)': 'MVN-2009-3063-CO-(ERRATUM)',
    'MVN 2010-1080 WLL/ MVN 2010 1032 WLL B': 'MVN-2010-1080-WLL_MVN-2010-1032-WLLB',
    'MVN-2010-1080-WLL/ MVN-2010-1032-WLL-A': 'MVN-2010-1080-WLL_MVN-2010-1032-WLL-A',
    'MVN-2010-01080- WLL, 2010-01032-WLL': 'MVN-2010-01080-WLL_2010-01032-WLL',
    '1997-3061-9 WB': 'MVN-1997-3061-9-WB',
    'MVN MCM 2013': 'MVN-MCM-2013',
    'MVN-2009-00436-MS_2': 'MVN-2009-00436-MS_2',
    'MVN-2008-01027 WKK NOD-25': 'MVN-2008-01027-WKK-NOD-25',
#   'MVN-2011-1995-EOO & MVN-2011-1974-EO': 'MVN-2011-1995-EOO_MVN-2011-1974-EO',
    'MVN-2011-1995-EOO & MVN-2011-1974-EOO': 'MVN-2011-1995-EOO_MVN-2011-1974-EO',
}

SKIP = {'0'}

PARISH = re.compile(r'^(acadia|allen|ascension|assumption|avoyelles|beauregard|bienville|bossier|caddo|calcasieu|caldwell|cameron|catahoula|claiborne|concordia|de soto|east baton rouge|east carroll|east feliciana|evangeline|franklin|grant|iberia|iberville|jackson|jefferson|jefferson davis|lafayette|lafourche|lasalle|lincoln|livingston|madison|morehouse|natchitoches|orleans|ouachita|plaquemines|pointe coupee|rapides|red river|richland|sabine|saint bernard|saint charles|saint helena|saint james|saint john the baptist|saint landry|saint martin|saint mary|saint tammany|tangipahoa|tensas|terrebonne|union|vermilion|vernon|washington|webster|west baton rouge|west carroll|west feliciana|winn)$')

def _parsedate(rawdate):
    return datetime.datetime.strptime(rawdate, '%m/%d/%Y')

def _clean_permit_application_number(n):
    'Clean up the permit application number.'
    if n in MANUAL_REPLACEMENTS:
        # If this is a manual one, replace it that way.
        return MANUAL_REPLACEMENTS[n]
    elif n[:3] in {'MVN', 'MVK'}:
        return _clean_mvn_permit_application_number(n)
    elif n[:3] == 'CEM':
        return _clean_cem_permit_application_number(n)
    else:
        raise AssertionError('Unexpected first block in %s' % n)

def _clean_cem_permit_application_number(n):
    'Clean up the permit application number for CEM permits.'
    for c in '/ \\':
        assert c not in n, n
    assert n.upper() == n
    return n

def _clean_mvn_permit_application_number(n):
    'Clean up the permit application number for MVN permits.'

    # Remove delimiters
    n = filter(lambda char: char not in '- ', n)

    # Add hyphen delimeters
    n = n[:3] + '-' + n[3:7] + '-' + n[7:]

    # If there's a fourth group
    if re.match(r'.+[0-9][A-Z]+$', n):
        # Add the delimiter
        n = re.sub(r'(.+[0-9])([A-Z]+)$', r'\1-\2', n)
    else:
        if not re.match(r'.+-[0-9]+$', n):
            raise AssertionError('The third group of %s is not all numbers.' % n)

    # Check year
    if n[:3] not in {'MVN', 'MVK'}:
        raise AssertionError('The first three letters of %s are not "MVN" or "MVK"' % n)

    # Check year
    if not re.match(PERMIT_YEAR, n[4:8]):
        raise AssertionError('The second group of %s doesn\'t seem like a year.' % n)

    # Final check
    if not re.match(PERMIT_APPLICATION_NUMBER_REGEX, n):
        raise AssertionError(
            'Permit application number %s could not be cleaned up.' % n
        )

    return n

def _onenode(html, xpath):
    nodes = html.xpath(xpath)
    if len(nodes) != 1:
        raise AssertionError('Not exactly one node')
    else:
        return nodes[0]

def _extract_parish(location):
    'Extract the parish name if it\'s a parish. Otherwise, return None.'
    if re.match(r'.+ Parish$', location):
        parish = re.sub(r' Parish$', '', location)
    else:
        parish = ''

    parish = parish.lower().replace('st.', 'saint')

    if re.match(PARISH, parish):
        return parish
    else:
        print(parish)
        return ''

def main():
    import os
    import sys
    import requests
    usage = 'USAGE: %s [filename] [web|terminal]' % sys.argv[0]
    if len(sys.argv) != 3:
        print usage
        exit(1)

    web = sys.argv[2] == 'web'
    terminal = sys.argv[2] == 'terminal'
    if not (web or terminal):
        print usage
        exit(1)

    listings_file = sys.argv[1]
    if not os.path.isfile(listings_file):
        print(usage)
        exit(1)

    f = open(listings_file)
    data = listing_parse(f.read().decode('latin1'))
    f.close()
    for doc in data:

        # These fields are required
        doc['type'] = 'impact'
        doc['flagged'] = 0
        doc['HUC'] = ''
        doc['AI'] = ''
        for k, v in doc.items():
            if v == None:
                doc[k] = ''

        if web:
            url = 'http://localhost:' + os.environ['PORT'] + '/applications/' + doc['permitApplicationNumber']
            response = requests.post(url, doc, auth = ('bot', os.environ['SCRAPER_PASSWORD']))
            print url, response.status_code
            # Print the error only if I care.
            if response.status_code != 204:
                if not 'already a permit application with number' in json.loads(response.text).get('message', ''):
                    print doc
                    print response.text

        elif terminal:
            if doc['permitApplicationNumber'] and doc['publicNoticeUrl'] and doc['drawingsUrl']:
                print doc['permitApplicationNumber'] + '\t' + doc['publicNoticeUrl'] + '\t' + doc['drawingsUrl']

if __name__== "__main__":
    main()
