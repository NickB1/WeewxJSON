from setup import ExtensionInstaller

def loader():
    return weewxJSONInstaller()

class weewxJSONInstaller(ExtensionInstaller):
    def __init__(self):
        super(weewxJSONInstaller, self).__init__(
            version="1.00",
            name='weewxJSON',
            description='Driver for HomeWizard or other JSON based weather stations.',
            author="Nick Blommen",
            author_email="nick.blommen1@gmail.com",
            config={
                'weewxJSON': {
                    'loop_interval': 'INSERT_LOOP_INTERVAL_HERE',
                    'url': 'INSERT_JSON_URL_HERE'
                    }
                },
            files=[('bin/user', ['bin/user/weewxJSON.py'])]
            )