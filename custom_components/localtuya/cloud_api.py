"""Class to perform requests to Tuya Cloud APIs."""
import functools
import hashlib
import hmac
import json
import logging
import time

import requests

from homeassistant.const import (
    CONF_ID,
)

from .const import (
    CONF_GW_ID,
    CONF_LOCAL_KEY,
    CONF_NODEID,
    CONF_SUB,
)

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

    async def async_get_access_token(self):
        """Obtain a valid access token."""
        try:
            resp = await self.async_make_request("GET", "/v1.0/token?grant_type=1")
        except requests.exceptions.ConnectionError:
            return "Request failed, status ConnectionError"

        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            return f"Error {r_json['code']}: {r_json['msg']}"

        self._access_token = resp.json()["result"]["access_token"]
        return "ok"

    async def async_get_devices_list(self):
        """Obtain the list of devices associated to a user."""
        resp = await self.async_make_request(
            "GET", url=f"/v1.0/users/{self._user_id}/devices"
        )

        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            # _LOGGER.debug(
            #     "Request failed, reply is %s",
            #     json.dumps(r_json, indent=2, ensure_ascii=False)
            # )
            return f"Error {r_json['code']}: {r_json['msg']}"

        self.device_list = {}

        for dev in r_json["result"]:
            dev[CONF_GW_ID] = ""
            dev_id = dev[CONF_ID]
            if dev[CONF_SUB] and CONF_NODEID in dev:
                # subdevice (Zigbee): will use the cid as the real id
                # dev_id = dev[CONF_NODEID]
                for dev2 in r_json["result"]:
                    if (
                        dev[CONF_LOCAL_KEY] == dev2[CONF_LOCAL_KEY]
                        and dev2["ip"] != ""
                        and CONF_NODEID not in dev2
                    ):
                        # _LOGGER.debug("FATHER IS %s", dev2[CONF_ID])
                        dev[CONF_GW_ID] = dev2[CONF_ID]

            self.device_list[dev_id] = dev

            # _LOGGER.debug("DEVICE: %s %s [%s]", dev_id, dev[CONF_LOCAL_KEY], dev[CONF_GW_ID])

        # _LOGGER.debug("DEV_LIST: %s", self.device_list)

        return "ok"
