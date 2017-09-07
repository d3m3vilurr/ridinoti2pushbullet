import os
import requests
import json
import re
from HTMLParser import HTMLParser
from pushbullet import PushBullet
import config as CONFIG

HOSTNAME = 'ridibooks.com'
AUTH_SERVER = 'https://' + HOSTNAME
MAIN_SERVER = 'http://' + HOSTNAME
API_SERVER = 'https://api.' + HOSTNAME

ACCESS_TOKEN_PATTERN = re.compile(r".+apiToken: '([^']+)'")
TAG_PATTERN = re.compile(r'<[^>]+>')
HTML_PARSER = HTMLParser()

b = PushBullet(CONFIG.PUSHBULLET_API)
if (CONFIG.PUSHBULLET_CHANNEL):
    b = b.get_channel(CONFIG.PUSHBULLET_CHANNEL)

def strip_html(m):
    return HTML_PARSER.unescape(TAG_PATTERN.sub('', m))

def fix_url(url):
    if (url[0] == '/'):
        if (url[1:20] == HOSTNAME):
            url = 'http:/' + url
        else:
            url = MAIN_SERVER + url
        url = url.replace('///', '//')
    return url

def push(title, message, landing=None):
    if (landing):
        landing = fix_url(landing)
    message += '\n' + landing
    b.push_note(title, message)

session = requests.Session()
session.post(AUTH_SERVER + '/account/login',
             dict(cmd='login',
                  user_id=CONFIG.RIDIBOOKS_ID,
                  passwd=CONFIG.RIDIBOOKS_PWD))

after_login = session.get(AUTH_SERVER).text.replace('\n', '')
m = ACCESS_TOKEN_PATTERN.match(after_login)
if not m:
    with open('dump.html', 'w') as w:
        w.write(after_login.encode('utf8'))
    raise SystemExit

access_token = 'Bearer ' + m.group(1)

headers = dict(
    authorization=access_token,
)

notis = session.get(API_SERVER + '/notifications?limit=100', headers=headers)
notis = json.loads(notis.text)

if not os.path.exists('.pushed'):
    PUSHED = []
else:
    with open('.pushed', 'r') as r:
        PUSHED = map(lambda x: x.strip(), r.readlines())

for noti in reversed(notis['notifications']):
    noti = json.loads(noti)
    item_id = noti['itemId']
    if item_id in PUSHED:
        continue
    _ = noti['message'].split('</strong>', 1)
    if len(_) < 2:
            _ = ('', _[0])
    title, message = _
    title = strip_html(title)
    message = strip_html(message)
    push(title, message, noti.get('landingUrl'))
    PUSHED.append(item_id)

with open('.pushed', 'w') as w:
    w.write('\n'.join(PUSHED[-200:]))
