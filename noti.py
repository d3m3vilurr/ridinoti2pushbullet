import os
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import json
import re
import html
from html.parser import HTMLParser
from pushbullet import PushBullet
import yaml
import time

HOSTNAME = 'ridibooks.com'
AUTH_SERVER = 'https://' + HOSTNAME
MAIN_SERVER = 'https://' + HOSTNAME
NOTIFICATION_PAGE_URL = MAIN_SERVER + '/notification/'
CHANGE_PWD_PAGE_URL = MAIN_SERVER + '/account/change-password'
API_SERVER = 'https://store-api.' + HOSTNAME
# TODO use selenium
TOKEN_URL = API_SERVER + '/users/me/notification-token/'

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
    return html.unescape(TAG_PATTERN.sub('', m)).strip()

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

def fetch_notifications():
    result = []

    firefox_options = Options()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(options=firefox_options)

    try:
        driver .implicitly_wait(20)

        driver.get(NOTIFICATION_PAGE_URL)
        driver .implicitly_wait(10)
        print(driver.current_url)
        driver.find_element_by_id('login_id').send_keys(RIDIBOOKS_ID)
        driver.find_element_by_id('login_pw').send_keys(RIDIBOOKS_PWD)
        # tricky; use the return in the password input form
        driver.find_element_by_id('login_pw').send_keys(Keys.ENTER)
        # or use the javascript action
        #driver.execute_script('$("button.login-button.main").click();')

        print('[+] wait login')
        # FIXME use unti
        for x in range(30):
            time.sleep(1)
            # skip the change pwd page
            if CHANGE_PWD_PAGE_URL in driver.current_url:
                driver.get(NOTIFICATION_PAGE_URL)
                continue
            if driver.current_url == NOTIFICATION_PAGE_URL:
                break
        else:
            print("[!] login failed")
            raise SystemExit
        print('[+] authorized')

        print('[+] wait loading notifications')
        # FIXME use unti
        for x in range(30):
            items = driver.find_elements_by_css_selector('main li')
            if len(items):
                break
            time.sleep(1)
        else:
            print('[!] loading notification failed')
            raise SystemExit

        print('[+] loaded: {} notis'.format(len(items)))

        for item in items:
            try:
                data_id = item.find_element_by_css_selector('div.notification-item').get_attribute('data-id')
                url = item.find_element_by_tag_name('a').get_attribute('href')
                text = item.find_element_by_tag_name('p').get_attribute('innerHTML')
                result.append(dict(data_id=data_id, url=url, message=text))
            except:
                # FIXME
                pass
    except:
        # anyway we must close the process
        driver.quit()
    return result

if not os.path.exists('.pushed'):
    PUSHED = []
else:
    with open('.pushed', 'r') as r:
        PUSHED = [x.strip() for x in r.readlines()]

for noti in reversed(fetch_notifications()):
    if not noti:
        continue
    item_id = noti['data_id']
    if item_id in PUSHED:
        continue
    _ = noti['message'].split('</strong>', 1)
    if len(_) < 2:
            _ = ('', _[0])
    title, message = _
    title = strip_html(title)
    message = strip_html(message)
    push(title, message, noti.get('url'))
    PUSHED.append(item_id)

with open('.pushed', 'w') as w:
    w.write('\n'.join(PUSHED[-200:]))
