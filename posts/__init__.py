class Sender(object):
    def __init__(self, setting):
        for k, v in setting.items():
            if k == 'type':
                continue
            setattr(self, 'config_{}'.format(k), v)

    def post(self, title, message, url):
        raise IOError('Not implement yet')
