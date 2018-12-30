from pushbullet import PushBullet
from posts import Sender

class PushBulletSender(Sender):
    def __init__(self, setting):
        super(PushBulletSender, self).__init__(setting)

        self.pushbullet = PushBullet(self.config_api)
        if hasattr(self, 'config_channel'):
            self.pushbullet = self.pushbullet.get_channel(self.config_channel)

    def post(self, title, message, url):
        if url:
            message = '{}\n{}'.format(message, url)
        self.pushbullet.push_note(title, message)

def make_sender(setting):
    return PushBulletSender(setting)
