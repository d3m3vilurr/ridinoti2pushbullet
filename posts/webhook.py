import requests
from posts import Sender

class WebhookSender(Sender):
    def __init__(self, setting):
        super(WebhookSender, self).__init__(setting)
        self.session = requests.session()

    def post(self, title, message, url):
        payload = self.make_payload(title, message, url)
        # probably hook method might be `post`
        self.session.post(self.config_url, json=payload)

    def make_payload(self, title, message):
        raise IOError('Not implement yet')
