import os
import requests
import json
import re
from html.parser import HTMLParser
from pushbullet import PushBullet
import yaml

HOSTNAME = 'ridibooks.com'
AUTH_SERVER = 'https://' + HOSTNAME
MAIN_SERVER = 'https://' + HOSTNAME
API_SERVER = 'https://api.' + HOSTNAME

ACCESS_TOKEN_PATTERN = re.compile(r".+apiToken: '([^']+)'")
NOTI_URL_PATTERN = re.compile(r".+notificationApiUrl: '([^']+)'")

TAG_PATTERN = re.compile(r'<[^>]+>')
HTML_PARSER = HTMLParser()

with open('config.yml') as f:
    CONFIG = yaml.safe_load(f.read())

RIDIBOOKS_ID = CONFIG['ridibooks']['id']
RIDIBOOKS_PWD = CONFIG['ridibooks']['password']

senders = []

for x in CONFIG.get('posts', ()):
    post_type = x.get('type')
    try:
        module = __import__('posts.{}'.format(post_type))
        module = getattr(module, post_type)
        senders.append(module.make_sender(x))
    except ModuleNotFoundError:
        print('not support {} yet'.format(post_type))

def strip_html(m):
    return HTML_PARSER.unescape(TAG_PATTERN.sub('', m)).strip()

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
    #message += '\n' + landing
    for sender in senders:
        sender.post(title, message, landing)

session = requests.Session()
session.post(AUTH_SERVER + '/account/login',
             dict(cmd='login', user_id=RIDIBOOKS_ID, passwd=RIDIBOOKS_PWD))

after_login = session.get(AUTH_SERVER).text.replace('\n', '')
m = ACCESS_TOKEN_PATTERN.match(after_login)
if not m:
    with open('dump.html', 'w') as w:
        w.write(after_login.encode('utf8'))
    raise SystemExit
access_token = 'Bearer ' + m.group(1)

m = NOTI_URL_PATTERN.match(after_login)
if not m:
    with open('dump.html', 'w') as w:
        w.write(after_login.encode('utf8'))
    raise SystemExit
noti_url = m.group(1)

headers = dict(
    authorization=access_token,
)

params = dict(
    limit=100,
)

notis = session.get(noti_url, headers=headers, params=params)
notis = notis.json()

if not os.path.exists('.pushed'):
    PUSHED = []
else:
    with open('.pushed', 'r') as r:
        PUSHED = [x.strip() for x in r.readlines()]

for noti in reversed(notis['notifications']):
    if not noti:
        continue
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
