"""Main to use the atome library."""
import argparse
import json
import logging
import sys

from pykeyatome import AtomeClient


def main():
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True, help="Atome username")
    parser.add_argument("-p", "--password", required=True, help="Password")
    parser.add_argument(
        "--debug", action="store_true", help="Print debug messages to stderr"
    )
    parser.add_argument(
        "action",
        type=str,
        default="live",
        help="Action",
        choices=["live","consumption"],
    )
    parser.add_argument(
        "--period",
        required=False,
        help="Period (only used with Action=consumption)",
        choices=["day","week","month","year"],
    )
    args = parser.parse_args()

    client = AtomeClient(args.username, args.password)

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
        if args.period not in ["day", "week", "month", "year"]:
            print("Please provide a proper period.")
        else:
            try:
                client.login()
                print(json.dumps(client.get_consumption(args.period), indent=2))

            except BaseException as exp:
                print(exp)
                return 1
            finally:
                client.close_session()
    else:
        print("Action not implemented %s", args.action)
        print(
            "Usage : __main__ -u username -p pwd [--debug] [live|consumption [day|week|month|year]]"
        )

if __name__ == "__main__":
    sys.exit(main())
