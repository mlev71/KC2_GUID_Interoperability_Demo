from __future__ import print_function
import sys
import json
import logging

from identifiers_client.local_server import is_remote_session
from identifiers_client.identifiers_api import (
    identifiers_client, IdentifierClientError, IdentifierNotLoggedIn)
from identifiers_client.config import config
from identifiers_client.login import (
    LOGGED_IN_RESPONSE, LOGGED_OUT_RESPONSE, check_logged_in,
    do_link_login_flow, do_local_server_login_flow, revoke_tokens)
from identifiers_client.helpers import (subcommand, argument,
                                        clear_internal_args)
from argparse import ArgumentParser

log = logging.getLogger(__name__)

cli = ArgumentParser()
subparsers = cli.add_subparsers(dest="subcommand")

_namespace_skin_props = [
    'header_background', 'header_icon_url', 'header_icon_link', 'header_text',
    'page_title', 'favicon_url', 'preamble_text'
]


@subcommand(
    [
        argument(
            '--force',
            action='store_true',
            default=False,
            help=('Do a fresh login, ignoring any existing credentials')),
        argument(
            "--no-local-server",
            action='store_true',
            default=False,
            help=("Manual login by copying and pasting an auth code. "
                  "This will be implied if using a remote connection.")),
    ],
    parent=subparsers,
    help=('Log in via Globus to get credentials for '
          'the Identifiers client'),
)
def login(args):
    # if not forcing, stop if user already logged in
    if not args.force and check_logged_in():
        print(LOGGED_IN_RESPONSE)
        return

    # use a link login if remote session or user requested
    if args.no_local_server or is_remote_session():
        do_link_login_flow()
    # otherwise default to a local server login flow
    else:
        do_local_server_login_flow()


@subcommand([], parent=subparsers, help='Log out of Identifier client')
def logout(args):
    revoke_tokens(config)
    config.set('tokens', 'access_token', '')
    config.set('tokens', 'access_token_expires', '0')
    config.set('tokens', 'refresh_token', '')
    config.save()
    print(LOGGED_OUT_RESPONSE)


@subcommand([
    argument(
        "--display-name",
        required=True,
        help="display_name of the new namespace"),
    argument(
        "--description",
        required=True,
        help="description of the new namespace"),
    argument(
        "--creators",
        required=True,
        help="The Principal URN for a Globus Group who's members "
        "are permitted to add to this namespace"),
    argument(
        "--admins",
        required=True,
        help="The Principal URN for a Globus Group who's members "
        "are permitted to perform administrative functions on "
        "this namespace"),
    argument(
        "--identifier-admins",
        required=True,
        help="The Principal URN for a Globus Group who's members "
        "are permitted to administrate identifiers created "
        "in this namespace"),
    argument(
        "--provider-type",
        required=True,
        help="The type of the provider used for minting "
        "identifiers"),
    argument(
        "--provider-config",
        help="Configuration for the provider used for "
        "minting identfiers in JSON format"),
    argument(
        "--header-background",
        help="HTML background color for header of landing page"),
    argument(
        "--header-icon-url",
        help="A URL for an image (icon) to be displayed in the "
        "header of the landing page"),
    argument(
        "--header-icon-link",
        help="A URL for a hyperlink when the header icon is "
        "clicked on in the landing page"),
    argument(
        "--header-text",
        help="A short text string to be placed in the header "
        "of the landing page next to the icon image"),
    argument(
        "--page-title",
        help="A short text string to be placed in the page "
        "(tab) title"),
    argument(
        "--favicon-url",
        help="A URL for the favicon to be discplayed in the "
        "page/tab title"),
    argument(
        "--preamble-text",
        help="Short text placed above the metadata of the "
        "identifier on the landing page")
],
            parent=subparsers)
def namespace_create(args):
    """
    Create a new namespace
    """
    client = identifiers_client(config)
    args = clear_internal_args(vars(args))
    # Convenience helper: If user doesn't specify a member
    # group, just use the same group as for admins.
    # This means all members will be admins.
    if 'creators' not in args:
        args['creators'] = args['admins']
    return client.create_namespace(**args)


@subcommand([
    argument(
        "--namespace-id",
        help="The id for the namespace to update",
        required=True),
    argument(
        "--display-name", help="The updated display_name of the namespace"),
    argument("--description", help="The updated description of the namespace"),
    argument(
        "--creators",
        help="The Principal URN for a Globus Group who's members are "
        "permitted to add to this namespace"),
    argument(
        "--admins",
        help="The Principal URN for a Globus Group who's members are "
        "permitted to perform administrative functions on "
        "this namespace"),
    argument(
        "--provider-type",
        help="The type of the provider used for minting "
        "identifiers"),
    argument(
        "--provider-config",
        help="Configuration for the provider used for "
        "minting identfiers in JSON format")
],
            parent=subparsers)
def namespace_update(args):
    """
    Update the properties of an existing namespace
    """
    client = identifiers_client(config)
    args = clear_internal_args(vars(args))

    # Convenience helper: If user doesn't specify a member
    # group, just use the same group as for admins.
    # This means all members will be admins.
    if 'creators' not in args:
        args['creators'] = args['admins']
    namespace_id = args.pop('namespace_id')

    return client.update_namespace(namespace_id, **args)


@subcommand([
    argument(
        "--namespace-id",
        help="The id for the namespace to display",
        required=True)
],
            parent=subparsers)
def namespace_display(args):
    """
    Display a namespace
    """
    client = identifiers_client(config)
    return client.get_namespace(args.namespace_id)


@subcommand([
    argument(
        "--namespace-id",
        help="The id for the namespace to update",
        required=True)
],
            parent=subparsers)
def namespace_delete(args):
    """
    Remove an existing namespace
    """
    client = identifiers_client(config)
    return client.delete_namespace(args.namespace_id)


@subcommand([
    argument(
        "--namespace",
        help="The id for the namespace in which to add the "
        "identifier",
        required=True),
    argument(
        "--location",
        help="A list of URLs from which the data referred to "
        "by the identifier may be retrieved"),
    argument(
        "--checksums",
        help='A JSON formatted list of {value, function} '
        '(e.g. \'[{"value": "<hashval>", "function": "sha256"}]\') '
        'pairs providing checksum values for the target data'),
    argument(
        "--visible-to",
        required=True,
        help='JSON List of users allowed to view the identifier '
        '(e.g. \'["public"]\')'),
    argument(
        "--metadata",
        help='Additional metadata associated with the '
        'identifier in JSON format '
        '(e.g. \'{"author": "John Doe", "year": 2018}\')')
],
            parent=subparsers)
def identifier_create(args):
    """
    Create a new identifier
    """
    client = identifiers_client(config)
    args = clear_internal_args(vars(args))
    return client.create_identifier(**args)


@subcommand([
    argument(
        "--identifier",
        help="The id for the identifier to update",
        required=True),
    argument(
        "--location",
        help="A URL from which the data referred to by the "
        "identifier may be retrieved"),
    argument(
        "--checksums",
        help="A JSON formatted list of {value, function} "
        "pairs providing checksum values for the target data"),
    argument(
        "--metadata",
        help="Additional metadata associated with the "
        "identifier in JSON format")
],
            parent=subparsers)
def identifier_update(args):
    """
    Update the state of an identifier
    """
    client = identifiers_client(config)
    identifier_id = args.identifier
    args = clear_internal_args(vars(args))

    return client.update_identifier(identifier_id, **args)


@subcommand([
    argument(
        "--identifier", help="The id for identifier to display", required=True)
],
            parent=subparsers)
def identifier_display(args):
    """
    Display the state of an identifier
    """
    client = identifiers_client(config)
    return client.get_identifier(args.identifier)


def main():
    args = cli.parse_args()
    subcommand = args.subcommand
    if subcommand is None:
        cli.print_help()
    else:
        try:
            ret = args.func(args)
            # These two don't make API calls:
            if subcommand not in ('login', 'logout'):
                print(json.dumps(ret.data, indent=2))
        except IdentifierNotLoggedIn as err:
            log.info(err)
            msg = "Not logged in. Use:\n  identifier login\nto log in."
            print(msg, file=sys.stderr)
        except IdentifierClientError as nce:
            print(
                'Command {} failed with HTTP Status code {}, details:\n{}'.
                format(subcommand, nce.http_status, nce.message),
                file=sys.stderr)
        except ValueError as ve:
            print(ve)


if __name__ == "__main__":
    main()
