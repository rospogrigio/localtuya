"""Cloud API implementation for Tuya OEM API."""
import functools
import logging
import hmac
import hashlib
import json

import requests
import time

from homeassistant.core import HomeAssistant

from .cloud_api import CloudApi

_TUYA_USER_AGENT = "TY-UA=APP/Android/1.1.6/SDK/null"
_TUYA_API_VERSION = "1.0"

_TUYA_KNOWN_VENDORS = {
    "ledvance": {
        "brand": "Ledvance",
        "client_id": "fx3fvkvusmw45d7jn8xh",
        "secret": "A_armptsqyfpxa4ftvtc739ardncett3uy_cgqx3ku34mh5qdesd7fcaru3gx7tyurr",
    }
}

_LOGGER = logging.getLogger(__name__)


class TuyaCloudApiOEM(CloudApi):
    """
    Class that logins and lists devices via the Tuya OEM API.

    The returned device list mimics that of the Tuya IoT Platform API.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        cloud_type: str,
        region: str,
        username: str,
        password: str,
        client_id: str,
        secret: str,
    ):
        """Initialize the class."""
        super().__init__(cloud_type)

        self._hass = hass
        self._endpoint = f"https://a1.tuya{region}.com/api.json"
        self._username = username
        self._password = password

        # It works with empty country code but the parameter must be sent nonetheless
        self._country_code = ""

        if cloud_type.startswith("oem_"):
            vendor = cloud_type.replace("oem_", "")
        else:
            raise ValueError("Cloud type must be one of the oem_xxx types")

        if vendor in _TUYA_KNOWN_VENDORS:
            self._client_id = _TUYA_KNOWN_VENDORS[vendor]["client_id"]
            self._secret = _TUYA_KNOWN_VENDORS[vendor]["secret"]
            self._brand = _TUYA_KNOWN_VENDORS[vendor]["brand"]
        elif vendor == "generic":
            self._client_id = client_id
            self._secret = secret
            self._brand = "generic"
        else:
            raise ValueError(f"Unknown vendor {vendor}")

        self._session = requests.session()
        self._sid = None

    async def _async_api(
        self, action, payload=None, extra_params=None, requires_sid=True
    ):
        headers = {"User-Agent": _TUYA_USER_AGENT}

        if extra_params is None:
            extra_params = {}

        params = {
            "a": action,
            "clientId": self._client_id,
            "v": _TUYA_API_VERSION,
            "time": str(int(time.time())),
            **extra_params,
        }

        if requires_sid:
            if self._sid is None:
                raise ValueError("You need to login first.")
            params["sid"] = self._sid

        data = {}
        if payload is not None:
            data["postData"] = json.dumps(payload, separators=(",", ":"))

        params["sign"] = self._sign({**params, **data})

        func = functools.partial(
            self._session.post,
            self._endpoint,
            params=params,
            data=data,
            headers=headers,
        )

        _LOGGER.debug("Request: headers %s, params %s, data %s", headers, params, data)

        result = await self._hass.async_add_executor_job(func)
        result = self._handle(result.json())

        _LOGGER.debug("Result: %s", result)

        return result

    def _sign(self, data):
        keys_not_to_sign = ["gid"]

        sorted_keys = sorted(list(data.keys()))

        # Create string to sign
        str_to_sign = ""
        for key in sorted_keys:
            if key in keys_not_to_sign:
                continue
            if key == "postData":
                if len(str_to_sign) > 0:
                    str_to_sign += "||"
                str_to_sign += key + "=" + self._mobile_hash(data[key])
            else:
                if len(str_to_sign) > 0:
                    str_to_sign += "||"
                str_to_sign += key + "=" + data[key]

        return hmac.new(
            bytes(self._secret, "utf-8"),
            msg=bytes(str_to_sign, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _mobile_hash(data):
        prehash = hashlib.md5(bytes(data, "utf-8")).hexdigest()
        return prehash[8:16] + prehash[0:8] + prehash[24:32] + prehash[16:24]

    @staticmethod
    def _handle(result):
        if result["success"]:
            return result["result"]
        if result["errorCode"] == "USER_SESSION_INVALID":
            raise InvalidUserSession(result["errorMsg"])
        if result["errorCode"] == "USER_PASSWD_WRONG":
            raise InvalidAuthentication(result["errorMsg"])
        raise ValueError(f"{result['errorMsg']} ({result['errorCode']})")

    @staticmethod
    def _plain_rsa_encrypt(modulus, exponent, message):
        """Encrypt message using plain (textbook) RSA encrypt."""
        message_int = int.from_bytes(message, "big")
        enc_message_int = pow(message_int, exponent, modulus)
        return enc_message_int.to_bytes(256, "big")

    def _enc_password(self, modulus, exponent, password):
        passwd_hash = hashlib.md5(password.encode("utf8")).hexdigest().encode("utf8")
        return self._plain_rsa_encrypt(int(modulus), int(exponent), passwd_hash).hex()

    async def _async_login(self):
        payload = {"countryCode": self._country_code, "email": self._username}
        token_info = await self._async_api(
            "tuya.m.user.email.token.create", payload, requires_sid=False
        )

        payload = {
            "countryCode": self._country_code,
            "email": self._username,
            "ifencrypt": 1,
            "options": '{"group": 1}',
            "passwd": self._enc_password(
                token_info["publicKey"], token_info["exponent"], self._password
            ),
            "token": token_info["token"],
        }
        login_info = await self._async_api(
            "tuya.m.user.email.password.login", payload, requires_sid=False
        )

        self._sid = login_info["sid"]

    async def _async_list_devices(self, retry_login=True):
        try:
            await self._async_list_devices_no_retry()
        except InvalidUserSession as err:
            # If session expired - retry login and operation once again
            if retry_login:
                _LOGGER.warning("User session expired, trying to re-login.")
                await self._async_login()
                await self._async_list_devices_no_retry()
            else:
                raise err

    async def _async_list_devices_no_retry(self):
        devs = {}
        # First fetch all "groups", i.e. homes
        for group in await self._async_api("tuya.m.location.list"):
            # Then fetch devices for each group and merge into a single list
            for dev in await self._async_api(
                "tuya.m.my.group.device.list", extra_params={"gid": group["groupId"]}
            ):
                # Map each device to the same format as the IoT Platform API
                devs[dev["devId"]] = self._map_device(dev)
        self._device_list = devs

    def _map_device(self, dev):
        category = dev["category"]
        model = f"{self._brand} {CloudApi.product_from_category(category)}"
        return {
            "id": dev["devId"],
            "category": category,
            "product_id": dev["productId"],
            "product_name": model,
            "model": model,
            "name": dev["name"],
            "local_key": dev["localKey"],
        }

    @staticmethod
    async def _invoke_handle_error(func: callable):
        try:
            await func()
        except ValueError as err:
            return str(err)

        return "ok"

    async def _async_authenticate(self):
        return await self._invoke_handle_error(self._async_login)

    async def _async_fetch_device_list(self):
        return await self._invoke_handle_error(self._async_list_devices)


class InvalidUserSession(ValueError):
    """Invalid user session error."""


class InvalidAuthentication(ValueError):
    """Invalid authentication error."""
