import markdown
from posts.webhook import WebhookSender

class MatrixWebhookSender(WebhookSender):
    def make_payload(self, title, message, url):
        if not url:
            text = '**{}**\n{}'.format(title, message)
        else:
            text = '**[{}]({})**\n{}'.format(title, url, message)
        payload = dict(format='html', text=markdown.markdown(text))
        if hasattr(self, 'config_name'):
            payload['displayName'] = self.config_name
        if hasattr(self, 'config_avatar'):
            payload['avatarUrl'] = self.config_avatar
        return payload

def make_sender(setting):
    return MatrixWebhookSender(setting)
