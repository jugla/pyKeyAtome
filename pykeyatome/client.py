"""Class client for atome protocol."""
import json
import logging

import requests
import simplejson
from fake_useragent import UserAgent

# export const
DAILY_PERIOD_TYPE = "day"
WEEKLY_PERIOD_TYPE = "week"
MONTHLY_PERIOD_TYPE = "month"
YEARLY_PERIOD_TYPE = "year"


# internal const
COOKIE_NAME = "PHPSESSID"
API_BASE_URI = "https://esoftlink.esoftthings.com"
API_ENDPOINT_LOGIN = "/api/user/login.json"
API_ENDPOINT_LIVE = "/measure/live.json"
API_ENDPOINT_CONSUMPTION = "/consumption.json"
LOGIN_URL = API_BASE_URI + API_ENDPOINT_LOGIN

DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3

_LOGGER = logging.getLogger(__name__)


class PyAtomeError(Exception):
    """Exception class."""

    pass


class AtomeClient(object):
    """The client class."""

    def __init__(
        self, username, password, atome_linky_number=1, session=None, timeout=None
    ):
        """Initialize the client object."""
        self.username = username
        self.password = password
        self._user_id = None
        self._user_reference = None
        self._session = session
        self._data = {}
        self._timeout = timeout
        # internal array start from 0 and not 1. Shift by 1.
        self._atome_linky_number = atome_linky_number - 1

    def login(self):
        """Set http session."""
        if self._session is None:
            self._session = requests.session()
            # adding fake user-agent header
            self._session.headers.update({"User-agent": str(UserAgent().random)})
        return self._login()

    def _login(self):
        """Login to Atome's API."""
        error_flag = False
        payload = {"email": self.username, "plainPassword": self.password}

        try:
            req = self._session.post(
                LOGIN_URL,
                json=payload,
                headers={"content-type": "application/json"},
                timeout=self._timeout,
            )
        except OSError:
            _LOGGER.debug("Can not login to API")
            error_flag = True
        if error_flag:
            return None

        try:
            response_json = req.json()

            user_id = str(response_json["id"])
            user_reference = response_json["subscriptions"][self._atome_linky_number][
                "reference"
            ]

            self._user_id = user_id
            self._user_reference = user_reference
        except (
            KeyError,
            OSError,
            json.decoder.JSONDecodeError,
            simplejson.errors.JSONDecodeError,
        ) as e:
            _LOGGER.debug(
                "Impossible to decode response: \nResponse was: [%s] %s",
                str(e),
                str(req.status_code),
                str(req.text),
            )
            error_flag = True
        if error_flag:
            return None

        return response_json

    def get_user_reference(self):
        return self._user_reference

    def _get_info_from_server(self, url, max_retries=0):
        error_flag = False

        if max_retries > MAX_RETRIES:
            _LOGGER.debug("Can't gather proper data. Max retries exceeded.")
            error_flag = True
            return None

        try:
            req = self._session.get(url, timeout=self._timeout)

        except OSError as e:
            _LOGGER.debug("Could not access Atome's API: " + str(e))
            error_flag = True
        if error_flag:
            return None

        if req.status_code == 403:
            # session is wrong, need to relogin
            self.login()
            logging.info("Got 403, relogging (max retries: %s)", str(max_retries))
            return self._get_info_from_server(url, max_retries + 1)

        if req.text == "":
            _LOGGER.debug("No data")
            error_flag = True
            return None

        try:
            json_output = req.json()
        except (
            OSError,
            json.decoder.JSONDecodeError,
            simplejson.errors.JSONDecodeError,
        ) as e:
            _LOGGER.debug(
                "Impossible to decode response: "
                + str(e)
                + "\nResponse was: "
                + str(req.text)
            )
            error_flag = True
        if error_flag:
            return None

        return json_output

    def get_live(self):
        """Get current data."""
        live_url = (
            API_BASE_URI
            + "/api/subscription/"
            + self._user_id
            + "/"
            + self._user_reference
            + API_ENDPOINT_LIVE
        )

        return self._get_info_from_server(live_url)

    def get_consumption(self, period):
        """Get current data."""
        if period not in [
            DAILY_PERIOD_TYPE,
            WEEKLY_PERIOD_TYPE,
            MONTHLY_PERIOD_TYPE,
            YEARLY_PERIOD_TYPE,
        ]:
            raise ValueError(
                "Period %s out of range. Shall be either 'day', 'week', 'month' or 'year'.",
                str(period),
            )
        consumption_url = (
            API_BASE_URI
            + "/api/subscription/"
            + self._user_id
            + "/"
            + self._user_reference
            + API_ENDPOINT_CONSUMPTION
            + "?period=so"
            + period[:1]
        )

        return self._get_info_from_server(consumption_url)

    def close_session(self):
        """Close current session."""
        self._session.close()
        self._session = None
