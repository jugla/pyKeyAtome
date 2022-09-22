"""Main to use the atome library."""
import argparse
import json
import logging
import sys

from pykeyatome.client import AtomeClient


def main():
    """Define the main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True, help="Atome username")
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument("-l", "--atome_linky_number", help="atome_linky_number")
    parser.add_argument(
        "--debug", action="store_true", help="Print debug messages to stderr"
    )
    parser.add_argument(
        "action",
        type=str,
        default="live",
        help="Action",
        choices=["live", "consumption"],
    )
    args = parser.parse_args()
    if args.atome_linky_number:
        atome_linky_number = int(args.atome_linky_number)
    else:
        atome_linky_number = 1
    client = AtomeClient(args.username, args.password, atome_linky_number)

    if args.debug:
        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    if args.action == "live":
        try:
            client.login()
            print(json.dumps(client.get_live(), indent=2))
        except BaseException as exp:
            print(exp)
            return 1
        finally:
            client.close_session()

    elif args.action == "consumption":
        try:
            client.login()
            print(json.dumps(client.get_consumption(), indent=2))

        except BaseException as exp:
            print(exp)
            return 1
        finally:
            client.close_session()
    else:
        print("Action not implemented %s", args.action)
        print(
            "Usage : __main__ -u username -p pwd [--debug] [live|consumption]"
        )


if __name__ == "__main__":
    sys.exit(main())
