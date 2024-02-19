import os
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import json
import re
import html
import hashlib
from html.parser import HTMLParser
from pushbullet import PushBullet
import time
from urllib.parse import urlparse, urlunparse
import yaml

HOSTNAME = 'ridibooks.com'
AUTH_SERVER = 'https://' + HOSTNAME
MAIN_SERVER = 'https://' + HOSTNAME
NOTIFICATION_PAGE_PATH = '/notification'
NOTIFICATION_PAGE_URL = MAIN_SERVER + NOTIFICATION_PAGE_PATH
CHANGE_PWD_PAGE_PATH = '/account/change-password'
CHANGE_PWD_PAGE_URL = MAIN_SERVER + CHANGE_PWD_PAGE_PATH
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
    except Exception as e:
        print('unknown exception: {}'.format(post_type))
        print(e)

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
        try:
            sender.post(title, message, landing)
        except:
            # TODO pushbullet has ratelimit
            pass

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
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="아이디"]').send_keys(RIDIBOOKS_ID)
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="비밀번호"]').send_keys(RIDIBOOKS_PWD)
        # tricky; use the return in the password input form
        driver.find_element(By.CSS_SELECTOR, 'input[placeholder="비밀번호"]').send_keys(Keys.ENTER)
        # or use the javascript action
        #driver.execute_script('$("button.login-button.main").click();')

        print('[+] wait login')
        # FIXME use unti
        for x in range(30):
            time.sleep(1)
            # skip the change pwd page
            parsed = urlparse(driver.current_url)
            #print(driver.current_url, parsed)
            print(driver.current_url)
            if parsed.path == CHANGE_PWD_PAGE_PATH:
                driver.get(NOTIFICATION_PAGE_URL)
                continue
            if parsed.path == NOTIFICATION_PAGE_PATH:
                break
        else:
            print("[!] login failed")
            raise SystemExit
        print('[+] authorized')

        print('[+] wait loading notifications')
        # FIXME use unti
        for x in range(30):
            sections = driver.find_elements(By.TAG_NAME, 'section')
            sections = [
                section
                for section in sections
                if not(len(section.find_elements(By.TAG_NAME, 'footer')))
            ]
            if len(sections):
                section = sections[0]
                items = section.find_elements(By.CSS_SELECTOR, 'li')
            if len(items):
                break
            time.sleep(1)
        else:
            print('[!] loading notification failed')
            raise SystemExit

        print('[+] loaded: {} notis'.format(len(items)))

        for item in items:
            try:
                url = item.find_element(By.TAG_NAME, 'a').get_attribute('href')
                # remove query strings
                parsed = urlparse(url)
                url = urlunparse(parsed._replace(query=''))
                data_id = hashlib.sha1(url.encode()).hexdigest()
                title = item.find_element(By.XPATH, './/a/div[2]/div').get_attribute('innerHTML')
                message = item.find_element(By.XPATH, './/a/div[2]/span').get_attribute('innerHTML')
                result.append(dict(data_id=data_id,
                                   url=url,
                                   title=title,
                                   message=message))
            except Exception as e:
                print(e)
                # FIXME
                pass
    except Exception as e:
        # anyway we must close the process
        print(e)
        driver.quit()
    return result

if not os.path.exists('.pushed'):
    PUSHED = []
else:
    with open('.pushed', 'r') as r:
        PUSHED = [x.strip() for x in r.readlines()]

for noti in reversed(fetch_notifications()):
    print(noti)
    if not noti:
        continue
    item_id = noti['data_id']
    if item_id in PUSHED:
        continue
    title = strip_html(noti['title'])
    message = strip_html(noti['message'])
    push(title, message, noti.get('url'))
    PUSHED.append(item_id)

with open('.pushed', 'w') as w:
    w.write('\n'.join(PUSHED[-200:]))
