import os
import requests
import json
import re
from HTMLParser import HTMLParser
from pushbullet import PushBullet
import config as CONFIG

TAG_PATTERN = re.compile(r'<[^>]+>')
HTML_PARSER = HTMLParser()

b = PushBullet(CONFIG.PUSHBULLET_API)
if (CONFIG.PUSHBULLET_CHANNEL):
    b = b.get_channel(CONFIG.PUSHBULLET_CHANNEL)

def strip_html(m):
    return HTML_PARSER.unescape(TAG_PATTERN.sub('', m))

def fix_url(url):
    if (url[0] == '/'):
        url = 'http://' + url
        url = url.replace('///', '//')
    return url

def push(title, message, image=None, landing=None):
    if (image):
        image = fix_url(image)
        b.push_file(file_url=image, file_name='', file_type="image/jpeg")
    if (landing):
        landing = fix_url(landing)
    message += '\n' + landing
    b.push_note(title, message)

session = requests.Session()
session.post('https://ridibooks.com/account/login',
             dict(cmd='login',
                  user_id=CONFIG.RIDIBOOKS_ID,
                  passwd=CONFIG.RIDIBOOKS_PWD))
notis = session.get('http://api.ridibooks.com/v0/notifications?limit=100')
notis = json.loads(notis.text)

if not os.path.exists('.pushed'):
    PUSHED = []
else:
    with open('.pushed', 'r') as r:
        PUSHED = map(lambda x: x.strip(), r.readlines())

for noti in reversed(notis['notifications']):
    noti = json.loads(noti)
    if noti['itemId'] in PUSHED:
        continue
    title, message = noti['message'].split('</strong>', 1)
    title = strip_html(title)
    message = strip_html(message)
    push(title, message, noti.get('imageUrl'), noti.get('landingUrl'))
    PUSHED.append(noti['itemId'])

with open('.pushed', 'w') as w:
    w.write('\n'.join(PUSHED[-100:]))
