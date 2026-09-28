from __future__ import print_function

import datetime
import getpass
import json
import math
import os
import re
import subprocess
import sys

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

try:
    text_type = unicode
    string_types = (basestring,)
    integer_types = (int, long)
    read_input = raw_input
except NameError:
    text_type = str
    string_types = (str,)
    integer_types = (int,)
    read_input = input

TARGETS = (
    ('74518642', '6475.74518642.442048412', 9567166),
    ('74518445', '6475.74518445.442046667', 12178498),
    ('74518534', '6475.74518534.442047078', 594815),
)
PROTECTED_ID = '7A748A1C3D0F44487B87C9571238719C00000000'
MARKER = b'\n__TM_CHECK_HTTP_STATUS__:'
MAX_RESPONSE = 32 * 1024 * 1024
RANGE_KEYS = set(('length', 'offset', 'start', 'end', 'from', 'to',
                  'position', 'begin', 'beginpos', 'endpos'))


class CheckError(Exception):
    pass


def normalized(key):
    return re.sub('[^a-z0-9]', '', text_type(key).lower())


def safe_key(key):
    # Field paths only: suppress unknown names that could contain business data.
    name = normalized(key)
    allowed = RANGE_KEYS | set((
        'data', 'result', 'results', 'items', 'events', 'event', 'objects',
        'entries', 'entry', 'markup', 'matches', 'match', 'segments',
        'contents', 'contentsrenderer', 'protectedobjects', 'protecteddocuments',
        'objectid', 'objectcontentid', 'contentid', 'sourceid', 'pobjectid',
        'protectedobjectidsource', 'protecteddocumentid', 'pdid', 'id',
        'type', 'status', 'code', 'meta', 'fields', 'headers', 'files', 'file',
        'attachments', 'attachment', 'facts', 'sourceattrs', 'unifiedattrs',
        'content', 'text', 'html', 'subject', 'body', 'message', 'messages',
    ))
    return name if name in allowed else '<field>'


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, integer_types):
        return value
    if isinstance(value, float) and not (math.isnan(value) or math.isinf(value)):
        return value
    if isinstance(value, string_types) and re.match(r'\A-?[0-9]{1,20}\Z', value):
        return int(value)
    return None


def kind(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, dict):
        return 'object'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, string_types):
        return 'string'
    if isinstance(value, integer_types):
        return 'integer'
    if isinstance(value, float):
        return 'number'
    return 'other'


def cfg_quote(value):
    if not isinstance(value, text_type):
        value = value.decode('utf-8')
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise CheckError('Control characters in local input; stopped.')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def request_event(host, event_id, headers, ca_file):
    params = [('headers[]', '*'), ('with[]', 'entries'),
              ('with[]', 'protected_documents'), ('with[]', 'contents_renderer')]
    url = 'https://%s/xapi/event/%s?%s' % (host, event_id, urlencode(params))
    cfg = [
        'silent', 'show-error', 'noproxy = "*"',
        'connect-timeout = 5', 'max-time = 45',
        'max-filesize = %d' % MAX_RESPONSE,
        'request = "GET"', 'url = ' + cfg_quote(url),
        'header = "Accept: application/json"',
        'write-out = "\\n__TM_CHECK_HTTP_STATUS__:%{http_code}"',
    ]
    if ca_file:
        cfg.append('cacert = ' + cfg_quote(ca_file))
    for name, value in headers:
        cfg.append('header = ' + cfg_quote(name + ': ' + value))

    try:
        proc = subprocess.Popen(
            ['curl', '-q', '--config', '-'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate(('\n'.join(cfg) + '\n').encode('utf-8'))
    except OSError:
        raise CheckError('Cannot start the existing curl executable.')
    if proc.returncode:
        if proc.returncode in (51, 60):
            raise CheckError('TLS verification failed (curl %d). Use the trusted '
                             'CA PEM and a hostname matching the TM certificate; '
                             'verification was NOT disabled.' % proc.returncode)
        raise CheckError('curl failed, exit=%d; raw response and stderr suppressed.'
                         % proc.returncode)
    body, sep, status = out.rpartition(MARKER)
    if not sep or not re.match(br'\A[0-9]{3}\Z', status):
        raise CheckError('Missing HTTP status trailer; raw output suppressed.')
    code = int(status)
    if code != 200:
        raise CheckError('TM returned HTTP %d; response body suppressed.' % code)
    if len(body) > MAX_RESPONSE:
        raise CheckError('Response exceeded the analysis size limit.')
    try:
        doc = json.loads(body.decode('utf-8'))
    except (ValueError, UnicodeError):
        raise CheckError('Response is not valid UTF-8 JSON; raw content suppressed.')
    return doc, len(body)


def summarize(doc, event_id, source_id, wanted_offset):
    totals = dict(nodes=0, length_fields=0, bad_lengths=0, offset_matches=0,
                  entries_nodes=0, protected_id_matches=0,
                  event_id_matches=0, source_id_matches=0)
    rows, structures = [], []
    limited = [False]

    def walk(value, path, depth):
        totals['nodes'] += 1
        if depth > 80 or totals['nodes'] > 300000:
            limited[0] = True
            return
        if isinstance(value, dict):
            nums = {}
            for key, item in value.items():
                nk = normalized(key)
                n = number(item)
                if nk in RANGE_KEYS and n is not None:
                    nums[nk] = n
                if nk == 'length':
                    totals['length_fields'] += 1
                    if n is not None and n < 1:
                        totals['bad_lengths'] += 1
                        if len(rows) < 60:
                            rows.append((path + '.' + safe_key(key),
                                         'length=%s; JSON type=%s' % (n, kind(item))))
                if n == wanted_offset:
                    totals['offset_matches'] += 1
                if nk == 'entries':
                    totals['entries_nodes'] += 1
                    if len(structures) < 8:
                        shape = kind(item)
                        if isinstance(item, list):
                            shape += '; count=%d' % len(item)
                            if item:
                                shape += '; first item=' + kind(item[0])
                                if isinstance(item[0], dict):
                                    shape += '; fields=' + ','.join(sorted(set(
                                        safe_key(k) for k in item[0])))
                        structures.append((path + '.' + safe_key(key), shape))
            if wanted_offset in nums.values() and len(rows) < 60:
                detail = ', '.join('%s=%s' % (k, nums[k]) for k in sorted(nums))
                rows.append((path, 'MATCHED OFFSET: ' + detail))
            for key, item in value.items():
                if totals['nodes'] > 300000:
                    limited[0] = True
                    break
                walk(item, path + '.' + safe_key(key), depth + 1)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if totals['nodes'] > 300000:
                    limited[0] = True
                    break
                walk(item, '%s[%d]' % (path, i), depth + 1)
        elif isinstance(value, string_types):
            if value.upper() == PROTECTED_ID:
                totals['protected_id_matches'] += 1
            if value == event_id:
                totals['event_id_matches'] += 1
            if value == source_id:
                totals['source_id_matches'] += 1
        elif number(value) == int(event_id):
            totals['event_id_matches'] += 1

    walk(doc, '$', 0)
    print('root JSON type:', kind(doc))
    for key in ('event_id_matches', 'source_id_matches', 'protected_id_matches',
                'entries_nodes', 'length_fields', 'bad_lengths', 'offset_matches'):
        print('%s: %d' % (key, totals[key]))
    print('SCAN COMPLETE:', not limited[0])
    print('--- ENTRIES STRUCTURE (values omitted) ---')
    for path, detail in structures:
        print(path + ' -> ' + detail)
    print('--- NUMERIC FINDINGS (at most 60 lines) ---')
    for path, detail in rows:
        print(path + ' -> ' + detail)
    if not rows:
        print('No matching numeric fields found. This does NOT clear the source.')
    return totals


def main():
    if not sys.stdin.isatty():
        raise CheckError('Run this file interactively from the SSH terminal.')
    print('Read-only GETs to TM. Enter EXISTING XAPI integration settings locally.')
    print('Not Linux credentials, not database passwords, not the service guard secret.')
    host = read_input('TM host [192.168.50.52]: ').strip() or '192.168.50.52'
    if not re.match(r'\A[A-Za-z0-9][A-Za-z0-9._-]*\Z', host):
        raise CheckError('Invalid hostname / IPv4 input.')
    ca_file = read_input('Trusted CA PEM path [system trust]: ').strip()
    if ca_file and not os.path.isfile(ca_file):
        raise CheckError('CA PEM file not found.')
    fields = [('apiVersion', 'X-API-Version'),
              ('apiCompanyID', 'X-API-CompanyId'),
              ('apiImporterName', 'X-API-ImporterName')]
    headers = []
    for label, name in fields:
        value = read_input(label + ': ').strip()
        if not value:
            raise CheckError('An existing XAPI setting was not supplied; stopped.')
        cfg_quote(value)
        headers.append((name, value))
    token = getpass.getpass('apiAuthToken (hidden): ')
    if not token:
        raise CheckError('No XAPI token; stopped.')
    cfg_quote(token)
    headers.append(('X-API-Auth-Token', token))
    del token
    for event_id, source_id, offset in TARGETS:
        print('\n=== TM EVENT %s ===' % event_id)
        print('checked UTC:', datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
        doc, size = request_event(host, event_id, headers, ca_file)
        print('HTTP: 200; UTF-8 JSON: OK; bytes:', size)
        summarize(doc, event_id, source_id, offset)
    print('\nDONE. No requests were made to FactsStorage; no events were changed.')


if __name__ == '__main__':
    try:
        main()
    except CheckError as exc:
        print('\nSTOP:', exc)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nStopped locally.')
        sys.exit(1)
    except Exception:
        print('\nSTOP: unexpected local error; raw data and credentials suppressed.')
        sys.exit(1)
