"""Class to retrieve devices and local keys through Tuya-based OEM mobile apps.

Some vendors (e.g. Ledvance and Sylvania) ship their own branded app, built on
the Tuya mobile SDK. Accounts of those apps cannot be linked to a Tuya IoT
Platform project, so the local keys are retrieved by logging in to the same
API used by the mobile app.

Based on https://github.com/FlagX/ha-ledvance-tuya-resync-localkey and
https://github.com/rgsilva/homeassistant-positivo.
"""
import hashlib
import hmac
import json
import logging
import time
import uuid

import requests

_LOGGER = logging.getLogger(__name__)

# App credentials extracted from the respective Android apps.
OEM_APPS = {
    "ledvance": {
        "name": "Ledvance",
        "client_id": "fx3fvkvusmw45d7jn8xh",
        "secret": "A_armptsqyfpxa4ftvtc739ardncett3uy_cgqx3ku34mh5qdesd7fcaru3gx7tyurr",
    },
    "sylvania": {
        "name": "Sylvania",
        "client_id": "creq75hn4vdg5qvrgryp",
        "secret": "A_ag4xcmp9rjttkj9yf9e8c3wfxry7yr44_wparh3scdv8dc7rrnuegaf9mqmn4snpk",
    },
}

ENDPOINTS = {
    "eu": "https://a1.tuyaeu.com/api.json",
    "us": "https://a1.tuyaus.com/api.json",
    "cn": "https://a1.tuyacn.com/api.json",
    "in": "https://a1.tuyain.com/api.json",
}

# Sessions shared between instances: the API rejects logins in quick succession,
# e.g. when the integration is set up right after validating the credentials.
_SESSIONS = {}

USER_AGENT = "TY-UA=APP/Android/1.1.6/SDK/null"
DEVICE_ID = "5fe5abb36728cce7b9cd2185625edccbd6d9bd787e40"
REQUEST_TIMEOUT = 15

KEYS_TO_SIGN = [
    "a",
    "v",
    "lat",
    "lon",
    "lang",
    "deviceId",
    "imei",
    "imsi",
    "appVersion",
    "ttid",
    "isH5",
    "h5Token",
    "os",
    "clientId",
    "postData",
    "time",
    "requestId",
    "n4h5",
    "sid",
    "sp",
    "et",
]


class OemApiError(Exception):
    """Error returned by the OEM app API."""

    def __init__(self, code, msg):
        """Initialize the error."""
        super().__init__(f"Error {code}: {msg}")
        self.code = code


def mobile_hash(data):
    """Calculate the shuffled MD5 hash used to sign postData."""
    prehash = hashlib.md5(bytes(data, "utf-8")).hexdigest()
    return prehash[8:16] + prehash[0:8] + prehash[24:32] + prehash[16:24]


def calc_sign(params, secret):
    """Calculate signature for request."""
    str_to_sign = "||".join(
        f"{key}={mobile_hash(params[key]) if key == 'postData' else params[key]}"
        for key in sorted(params)
        if key in KEYS_TO_SIGN and params[key] is not None and str(params[key]) != ""
    )
    return hmac.new(
        bytes(secret, "utf-8"),
        msg=bytes(str_to_sign, "utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def encrypt_password(public_key, exponent, password):
    """Encrypt the password the way the app does (textbook RSA of its MD5)."""
    md5_hex = hashlib.md5(password.encode("utf-8")).hexdigest().encode("utf-8")
    encrypted = pow(int.from_bytes(md5_hex, "big"), int(exponent), int(public_key))
    return "0" * 64 + encrypted.to_bytes((encrypted.bit_length() + 7) // 8, "big").hex()


class TuyaOemCloudApi:
    """Class to send API calls to the Tuya mobile app API of an OEM app."""

    def __init__(self, hass, region_code, provider, email, password, country_code):
        """Initialize the class."""
        self._hass = hass
        self._endpoint = ENDPOINTS.get(region_code, ENDPOINTS["eu"])
        self._client_id = OEM_APPS[provider]["client_id"]
        self._secret = OEM_APPS[provider]["secret"]
        self._provider_name = OEM_APPS[provider]["name"]
        self._email = email
        self._password = password
        self._country_code = str(country_code)
        self._session = requests.Session()
        self._session_key = (
            self._endpoint,
            self._client_id,
            email,
            hashlib.sha256(str(password).encode("utf-8")).hexdigest(),
        )
        self._sid = _SESSIONS.get(self._session_key)
        self.device_list = {}

    def _request(
        self, action, post_data=None, version="1.0", requires_sid=True, params=None
    ):
        """Perform a signed request, with optional extra (unsigned) query params."""
        extra_params = params or {}
        params = {
            "a": action,
            "appVersion": "1.1.6",
            "appRnVersion": "5.14",
            "channel": "oem",
            "deviceId": DEVICE_ID,
            "platform": "Linux",
            "requestId": str(uuid.uuid4()),
            "lang": "en",
            "clientId": self._client_id,
            "osSystem": "9",
            "os": "Android",
            "timeZoneId": str(self._hass.config.time_zone),
            "ttid": "sdk_tuya@" + self._client_id,
            "et": "0.0.1",
            "v": version,
            "sdkVersion": "3.10.0",
            "time": str(int(time.time())),
            **extra_params,
        }
        if requires_sid:
            params["sid"] = self._sid

        data = None
        if post_data is not None:
            data = {"postData": json.dumps(post_data, separators=(",", ":"))}
        params["sign"] = calc_sign({**params, **(data or {})}, self._secret)

        resp = self._session.post(
            self._endpoint,
            params=params,
            data=data,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        r_json = resp.json()
        if not r_json.get("success"):
            raise OemApiError(r_json.get("errorCode"), r_json.get("errorMsg"))
        return r_json["result"]

    def _api(self, action, post_data=None, version="1.0", params=None):
        """Perform a request, logging in again if the session has expired."""
        if self._sid is None:
            self._login()
        try:
            return self._request(action, post_data, version, params=params)
        except OemApiError as ex:
            if ex.code != "USER_SESSION_INVALID":
                raise
            _LOGGER.debug("%s session expired, logging in again", self._provider_name)
            self._login()
            return self._request(action, post_data, version, params=params)

    def _login(self):
        """Log in with email and password."""
        self._sid = None
        _SESSIONS.pop(self._session_key, None)
        _LOGGER.debug("Logging in to %s app API", self._provider_name)
        token_info = self._request(
            "tuya.m.user.email.token.create",
            {"countryCode": int(self._country_code), "email": self._email},
            requires_sid=False,
        )
        login_info = self._request(
            "tuya.m.user.email.password.login",
            {
                "countryCode": self._country_code,
                "email": self._email,
                "ifencrypt": 1,
                "options": '{"group": 1}',
                "passwd": encrypt_password(
                    token_info["publicKey"], token_info["exponent"], self._password
                ),
                "token": token_info["token"],
            },
            requires_sid=False,
        )
        self._sid = login_info["sid"]
        _SESSIONS[self._session_key] = self._sid

    def _get_devices(self):
        """Retrieve all devices of all homes of the account."""
        devices = {}
        for group in self._api("tuya.m.location.list"):
            group_devs = self._api(
                "tuya.m.my.group.device.list", params={"gid": group["groupId"]}
            )
            for dev in group_devs:
                if not dev.get("localKey"):
                    dev = self._api("tuya.m.device.get", {"devId": dev["devId"]})
                devices[dev["devId"]] = {
                    "id": dev["devId"],
                    "name": dev.get("name"),
                    "local_key": dev.get("localKey"),
                    "product_id": dev.get("productId"),
                    "product_name": dev.get("productName") or self._provider_name,
                    "online": dev.get("isOnline"),
                }
        return devices

    async def _async_call(self, func):
        """Run a blocking call in the executor and convert errors to a message."""
        try:
            await self._hass.async_add_executor_job(func)
        except OemApiError as ex:
            return str(ex)
        except requests.exceptions.RequestException as ex:
            return f"Request failed: {ex}"
        except (KeyError, ValueError) as ex:
            return f"Unexpected response: {ex!r}"
        return "ok"

    async def async_get_access_token(self):
        """Log in to the OEM app API, unless a session is already available."""
        if self._sid is not None:
            return "ok"
        return await self._async_call(self._login)

    async def async_get_devices_list(self):
        """Obtain the list of devices associated to the account."""

        def _update():
            self.device_list = self._get_devices()

        return await self._async_call(_update)
