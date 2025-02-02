"""Class to perform requests to Tuya Cloud APIs."""
import asyncio
import functools
import hashlib
import hmac
import json
import logging
import time

import requests

_LOGGER = logging.getLogger(__name__)


# Signature algorithm.
def calc_sign(msg, key):
    """Calculate signature for request."""
    sign = (
        hmac.new(
            msg=bytes(msg, "latin-1"),
            key=bytes(key, "latin-1"),
            digestmod=hashlib.sha256,
        )
        .hexdigest()
        .upper()
    )
    return sign


class TuyaCloudApi:
    """Class to send API calls."""

    def __init__(self, hass, region_code, client_id, secret, user_id):
        """Initialize the class."""
        self._hass = hass
        self._base_url = f"https://openapi.tuya{region_code}.com"
        self._client_id = client_id
        self._secret = secret
        self._user_id = user_id
        self._access_token = ""
        self._token_expire_time: int = 0

        self.device_list = {}

    def generate_payload(self, method, timestamp, url, headers, body=None):
        """Generate signed payload for requests."""
        payload = self._client_id + self._access_token + timestamp

        payload += method + "\n"
        # Content-SHA256
        payload += hashlib.sha256(bytes((body or "").encode("utf-8"))).hexdigest()
        payload += (
            "\n"
            + "".join(
                [
                    "%s:%s\n" % (key, headers[key])  # Headers
                    for key in headers.get("Signature-Headers", "").split(":")
                    if key in headers
                ]
            )
            + "\n/"
            + url.split("//", 1)[-1].split("/", 1)[-1]  # Url
        )
        # _LOGGER.debug("PAYLOAD: %s", payload)
        return payload

    async def async_make_request(self, method, url, body=None, headers={}):
        """Perform requests."""
        # obtain new token if expired.
        if not self.token_validate and self._token_expire_time != -1:
            if (res := await self.async_get_access_token()) and res != "ok":
                return _LOGGER.debug(f"Refresh Token failed due to: {res}")

        timestamp = str(int(time.time() * 1000))
        payload = self.generate_payload(method, timestamp, url, headers, body)
        default_par = {
            "client_id": self._client_id,
            "access_token": self._access_token,
            "sign": calc_sign(payload, self._secret),
            "t": timestamp,
            "sign_method": "HMAC-SHA256",
        }
        full_url = self._base_url + url
        # _LOGGER.debug("\n" + method + ": [%s]", full_url)

        if method == "GET":
            func = functools.partial(
                requests.get, full_url, headers=dict(default_par, **headers)
            )
        elif method == "POST":
            func = functools.partial(
                requests.post,
                full_url,
                headers=dict(default_par, **headers),
                data=json.dumps(body),
            )
            # _LOGGER.debug("BODY: [%s]", body)
        elif method == "PUT":
            func = functools.partial(
                requests.put,
                full_url,
                headers=dict(default_par, **headers),
                data=json.dumps(body),
            )

        resp = await self._hass.async_add_executor_job(func)
        # r = json.dumps(r.json(), indent=2, ensure_ascii=False) # Beautify the format
        return resp

    async def async_get_access_token(self) -> str | None:
        """Obtain a valid access token."""
        # Reset access token
        self._token_expire_time = -1
        self._access_token = ""

        try:
            resp = await self.async_make_request("GET", "/v1.0/token?grant_type=1")
        except requests.exceptions.ConnectionError:
            self._token_expire_time = 0
            return "Request failed, status ConnectionError"

        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            return f"Error {r_json['code']}: {r_json['msg']}"

        req_results = r_json["result"]

        expire_time = int(req_results.get("expire_time", 3600))
        self._token_expire_time = int(time.time()) + expire_time
        self._access_token = resp.json()["result"]["access_token"]
        return "ok"

    async def async_get_devices_list(self) -> str | None:
        """Obtain the list of devices associated to a user."""
        resp = await self.async_make_request(
            "GET", url=f"/v1.0/users/{self._user_id}/devices"
        )

        if not resp:
            return
        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            # _LOGGER.debug(
            #     "Request failed, reply is %s",
            #     json.dumps(r_json, indent=2, ensure_ascii=False)
            # )
            return f"Error {r_json['code']}: {r_json['msg']}"

        self.device_list = {dev["id"]: dev for dev in r_json["result"]}

        # Get Devices DPS Data.
        get_functions = [self.get_device_functions(devid) for devid in self.device_list]
        await asyncio.gather(*get_functions)

        return "ok"

    async def async_get_device_specifications(self, device_id) -> dict[str, dict]:
        """Obtain the DP ID mappings for a device."""
        resp = await self.async_make_request(
            "GET", url=f"/v1.1/devices/{device_id}/specifications"
        )

        if not resp:
            return
        if not resp.ok:
            return {}, "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            return {}, f"Error {r_json['code']}: {r_json['msg']}"

        return r_json["result"], "ok"

    async def async_get_device_query_properties(self, device_id) -> dict[dict, str]:
        """Obtain the DP ID mappings for a device correctly!."""
        resp = await self.async_make_request(
            "GET", url=f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        )

        if not resp:
            return
        if not resp.ok:
            return {}, "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            return {}, f"Error {r_json['code']}: {r_json['msg']}"

        return r_json["result"], "ok"

    async def get_device_functions(self, device_id) -> dict[str, dict]:
        """Pull Devices Properties and Specifications to devices_list"""
        get_data = [
            self.async_get_device_specifications(device_id),
            self.async_get_device_query_properties(device_id),
        ]
        specs, query_props = await asyncio.gather(*get_data)
        if query_props[1] == "ok":
            device_data = {str(p["dp_id"]): p for p in query_props[0].get("properties")}
        if specs[1] == "ok":
            for func in specs[0].get("functions"):
                if str(func["dp_id"]) in device_data:
                    device_data[str(func["dp_id"])].update(func)

        if device_data:
            self.device_list[device_id]["dps_data"] = device_data

        return device_data

    async def async_connect(self):
        """Connect to cloudAPI"""
        if (res := await self.async_get_access_token()) and res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
            return "authentication_failed", res

        if (res := await self.async_get_devices_list()) and res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
            return "device_list_failed", res

        _LOGGER.info("Cloud API connection succeeded.")
        return True, res

    @property
    def token_validate(self):
        """Return whether token is expired or not"""
        cur_time = int(time.time())
        expire_time = self._token_expire_time - 30

        return expire_time >= cur_time
