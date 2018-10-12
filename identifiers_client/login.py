from __future__ import print_function
import platform
import webbrowser
import sys

from six.moves import input
from globus_sdk import NativeAppAuthClient

from identifiers_client.config import config
from identifiers_client.local_server import (start_local_server,
                                             LocalServerError)


def _login_client(config):
    client_id = config.get('client', 'client_id')
    return NativeAppAuthClient(client_id, app_name='identifier_client_dev')


_SHARED_EPILOG = ("""\
Logout of the Identifier client with
  globus-identifier-client logout
""")

_LOGIN_EPILOG = (u"""\

You have successfully logged in to the Identifier client
""") + _SHARED_EPILOG

LOGGED_IN_RESPONSE = ("""\
You are already logged in!

You may force a new login with
  globus-identifier-client login --force
""") + _SHARED_EPILOG

LOGGED_OUT_RESPONSE = ("""\
You have successfully logged out of the Identifier client.

You can log in again with
  globus-identifier-client login
""")


def check_logged_in():
    # first, pull up all of the data from config and see what we can get
    # we can skip the access tokens and their expiration times as those are not
    # strictly necessary
    refresh_token = config.get('tokens', 'REFRESH_TOKEN')
    access_token = config.get('tokens', 'ACCESS_TOKEN')
    if not (refresh_token and access_token):
        return False

    # check that at least refresh token is valid
    native_client = _login_client(config)
    res = native_client.oauth2_validate_token(refresh_token)
    if not res['active']:
        return False

    return True


def do_link_login_flow():
    """
    Prompts the user with a link to authorize the CLI to act on their behalf.
    """
    # get the NativeApp client object
    native_client = _login_client()

    # start the Native App Grant flow, prefilling the
    # named grant label on the consent page if we can get a
    # hostname for the local system
    label = platform.node() or None
    native_client.oauth2_start_flow(
        refresh_tokens=True, prefill_named_grant=label)

    # prompt
    linkprompt = 'Please log into Globus here'
    tmpl = '{0}:\n{1}\n{2}\n{1}\n'
    print(
        tmpl.format(linkprompt, '-' * len(linkprompt),
                    native_client.oauth2_get_authorize_url()))

    # come back with auth code
    prompt = 'Enter the resulting Authorization Code here'
    auth_code = input(prompt).strip()

    # finish login flow
    exchange_code_and_store_config(native_client, auth_code)


def do_local_server_login_flow():
    """
    Starts a local http server, opens a browser to have the user login,
    and gets the code redirected to the server (no copy and pasting required)
    """
    print(
        "You are running 'identifier login', which should automatically open "
        "a browser window for you to login.\n"
        "If this fails or you experience difficulty, try "
        "'identifier login --no-local-server'"
        "\n---")
    # start local server and create matching redirect_uri
    with start_local_server(listen=('127.0.0.1', 0)) as server:
        _, port = server.socket.getsockname()
        redirect_uri = 'http://localhost:{}'.format(port)

        # get the NativeApp client object and start a flow
        # if available, use the system-name to prefill the grant
        label = platform.node() or None
        native_client = _login_client(config)
        native_client.oauth2_start_flow(
            requested_scopes=config.get('client', 'scope'),
            refresh_tokens=True,
            prefill_named_grant=label,
            redirect_uri=redirect_uri)
        url = native_client.oauth2_get_authorize_url()

        # open web-browser for user to log in, get auth code
        webbrowser.open(url, new=1)
        auth_code = server.wait_for_code()

    if isinstance(auth_code, LocalServerError):
        print('Login failed: {}'.format(auth_code), file=sys.stderr)
        sys.exit(1)
    elif isinstance(auth_code, Exception):
        msg = 'Login failed with unexpected error:\n{}'.format(auth_code)
        print(msg, file=sys.stderr)
        sys.exit(1)

    # finish login flow
    exchange_code_and_store_config(native_client, auth_code)


def exchange_code_and_store_config(native_client, auth_code):
    """
    Finishes login flow after code is gotten from command line or local server.
    Exchanges code for tokens and gets user info from auth.
    Stores tokens and user info in config.
    """
    # do a token exchange with the given code
    tkn = native_client.oauth2_exchange_code_for_tokens(auth_code)

    # Revoke any existing tokens
    revoke_tokens(config)

    extract_and_save_tokens(tkn, config)

    print(_LOGIN_EPILOG)
    return tkn


def extract_and_save_tokens(tkn, config):
    tkn = tkn.by_scopes[config.get('client', 'scope')]

    # extract tokens from response
    access_token = tkn['access_token']
    refresh_token = tkn['refresh_token']

    config.set('tokens', 'access_token', access_token)
    config.set('tokens', 'access_token_expires',
               str(tkn['expires_at_seconds']))
    config.set('tokens', 'refresh_token', refresh_token)
    config.save()


def revoke_tokens(config):
    native_client = _login_client(config)
    access_token = config.get('tokens', 'access_token')
    refresh_token = config.get('tokens', 'refresh_token')
    if access_token:
        native_client.oauth2_revoke_token(access_token)
    if refresh_token:
        native_client.oauth2_revoke_token(refresh_token)
