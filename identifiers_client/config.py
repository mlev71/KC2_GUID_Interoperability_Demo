from os import path, environ
from six.moves.configparser import ConfigParser

_default = path.join(path.expanduser('~'), '.globus_identifier')
IDENTIFIER_CONFIG_FILE = path.abspath(
    environ.get('IDENTIFIER_CONFIG_FILE', _default))
IDENTIFIER_ENVIRONMENT = environ.get('IDENTIFIER_ENVIRONMENT', 'production')

_identifier_environments = {
    'dev': {
        'service_url': ('http://localhost:5000/'),
        #        'client_id': '8bd25a6b-591d-4267-82a6-285a813acace',
        'client_id':
        'b61613f8-0da8-4be7-81aa-1c89f2c0fe9f',
        'scope':
        ('https://auth.globus.org/scopes/identifiers.globus.org/create_update')
    },
    'production': {
        'service_url':
        'https://identifiers.globus.org/',
        'client_id':
        'b61613f8-0da8-4be7-81aa-1c89f2c0fe9f',
        'scope':
        ('https://auth.globus.org/scopes/identifiers.globus.org/create_update')
    }
}


def _set_defaults(cfg):
    env = _identifier_environments[IDENTIFIER_ENVIRONMENT]
    config.add_section('client')
    cfg.set('client', "service_url", env["service_url"])
    cfg.set('client', "client_id", env["client_id"])
    cfg.set('client', "scope", env["scope"])
    config.add_section('tokens')
    cfg.set('tokens', 'access_token', '')
    cfg.set('tokens', 'access_token_expires', '0')
    cfg.set('tokens', 'refresh_token', '')


config = ConfigParser()


def _save():
    with open(IDENTIFIER_CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


# Monkey-patch config so other things can call
# config.save() without having to care about file
# location.
config.save = _save

if path.exists(IDENTIFIER_CONFIG_FILE):
    config.read(IDENTIFIER_CONFIG_FILE)
else:
    _set_defaults(config)
