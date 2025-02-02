"""Class to perform requests to Tuya Cloud APIs."""

import asyncio
import functools
import hashlib
import hmac
import json
import logging
import time

import requests
from requests.adapters import HTTPAdapter, Retry


DEVICES_UPDATE_INTERVAL = 300
DEVICES_UPDATE_INTERVAL_FORCED = 10

TUYA_ENDPOINTS = {
    # Regions code
    "Central Europe Data Center": "eu",
    "China Data Center": "cn",
    "Eastern America Data Center": "ea",
    "India Data Center": "in",
    "Western America Data Center": "us",
    "Western Europe Data Center": "we",
}


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


class CustomAdapter(logging.LoggerAdapter):
    """Adapter logger for cloud api."""

    def process(self, msg, kwargs):
        return f"[{self.extra.get('prefix', '')}] {msg}", kwargs


class TuyaCloudApi:
    """Class to send API calls."""

    def __init__(self, hass, region_code, client_id, secret, user_id):
        """Initialize the class."""
        self._logger = CustomAdapter(
            logging.getLogger(__name__), {"prefix": user_id[:3] + "..." + user_id[-3:]}
        )

        self._hass = hass
        self._client_id = client_id
        self._secret = secret
        self._user_id = user_id
        self._access_token = ""
        self._token_expire_time: int = 0

        if region_code == "ea":
            self._base_url = "https://openapi-ueaz.tuyaus.com"
        elif region_code == "we":
            self._base_url = "https://openapi-weaz.tuyaeu.com"
        else:
            self._base_url = f"https://openapi.tuya{region_code}.com"

        self.device_list = {}
        self.cached_device_list = {}

        self._last_devices_update = int(time.time())

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
        # self._logger.debug("PAYLOAD: %s", payload)
        return payload

    async def async_make_request(self, method, url, body=None, headers={}):
        """Perform requests."""
        # obtain new token if expired.
        if not self.token_validate and self._token_expire_time != -1:
            if (res := await self.async_get_access_token()) and res != "ok":
                return self._logger.debug(f"Refresh Token failed due to: {res}")

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
        max_retries = 3
        request_timeout = 3

        # Create requests session.
        request_session = requests.Session()
        # Setup retries configuration
        retries = Retry(total=max_retries, backoff_factor=0.3)
        request_session.mount(full_url, HTTPAdapter(max_retries=retries))
        if method == "GET":
            func = functools.partial(
                request_session.get,
                full_url,
                headers=dict(default_par, **headers),
                timeout=request_timeout,
            )
        elif method == "POST":
            func = functools.partial(
                request_session.post,
                full_url,
                headers=dict(default_par, **headers),
                data=json.dumps(body),
                timeout=request_timeout,
            )
            # self._logger.debug("BODY: [%s]", body)
        elif method == "PUT":
            func = functools.partial(
                request_session.put,
                full_url,
                headers=dict(default_par, **headers),
                data=json.dumps(body),
                timeout=request_timeout,
            )

        try:
            resp = await self._hass.async_add_executor_job(func)
        except requests.exceptions.ReadTimeout as ex:
            self._logger.debug(f"Requests read timeout: {ex}")
            return
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

        if not resp:
            self._token_expire_time = 0
            return
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

    async def async_get_devices_list(self, force_update=False) -> str | None:
        """Obtain the list of devices associated to a user. - force_update will ignore last update check."""
        interval = (
            DEVICES_UPDATE_INTERVAL
            if not force_update
            else DEVICES_UPDATE_INTERVAL_FORCED
        )
        if (
            self.device_list
            and int(time.time()) - (self._last_devices_update + interval) < 0
        ):
            return self._logger.debug(f"Devices has been updated a minutes ago.")

        resp = await self.async_make_request(
            "GET", url=f"/v1.0/users/{self._user_id}/devices"
        )

        if not resp:
            return
        if not resp.ok:
            return "Request failed, status " + str(resp.status)

        r_json = resp.json()
        if not r_json["success"]:
            # self._logger.debug(
            #     "Request failed, reply is %s",
            #     json.dumps(r_json, indent=2, ensure_ascii=False)
            # )
            return f"Error {r_json['code']}: {r_json['msg']}"

        self.device_list = {dev["id"]: dev for dev in r_json["result"]}

        # Get Devices DPS Data.
        get_functions = [
            self._hass.async_create_task(self.get_device_functions(devid))
            for devid in self.device_list
        ]
        # await asyncio.run(*get_functions)

        self._last_devices_update = int(time.time())
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
        """Obtain the DP ID mappings for a device correctly! Note: This won't works if the subscription expired."""
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

    async def async_get_device_query_things_data_model(
        self, device_id
    ) -> dict[str, dict]:
        """Obtain the DP ID mappings for a device."""
        resp = await self.async_make_request(
            "GET", url=f"/v2.0/cloud/thing/{device_id}/model"
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
        cached = device_id in self.cached_device_list
        if cached and (dps_data := self.cached_device_list[device_id].get("dps_data")):
            self.device_list[device_id]["dps_data"] = dps_data
            return

        device_data = {}
        get_data = [
            self.async_get_device_specifications(device_id),
            self.async_get_device_query_properties(device_id),
            self.async_get_device_query_things_data_model(device_id),
        ]
        try:
            specs, query_props, query_model = await asyncio.gather(*get_data)
        except requests.exceptions.ConnectionError as ex:
            self._logger.debug(f"Failed to get DPS functions for {device_id} - {ex}")
            return

        if query_props[1] == "ok":
            device_data = {str(p["dp_id"]): p for p in query_props[0].get("properties")}
        if specs[1] == "ok":
            for func in specs[0].get("functions", {}):
                if str(func.get("dp_id")) in device_data:
                    device_data[str(func["dp_id"])].update(func)
                elif dp_id := func.get("dp_id"):
                    device_data[str(dp_id)] = func
        if query_model[1] == "ok":
            model_data = json.loads(query_model[0]["model"])
            services = model_data.get("services", [{}])[0]
            properties = services.get("properties")
            for dp_data in properties if properties else {}:
                refactored = {
                    "id": dp_data.get("abilityId"),
                    # "code": dp_data.get("code"),
                    "accessMode": dp_data.get("accessMode"),
                    # values: json.loads later
                    "values": str(dp_data.get("typeSpec")).replace("'", '"'),
                }
                if str(dp_data["abilityId"]) in device_data:
                    device_data[str(dp_data["abilityId"])].update(refactored)
                else:
                    refactored["code"] = dp_data.get("code")
                    device_data[str(dp_data["abilityId"])] = refactored

        if "28841002" in str(query_props[1]):
            # No permissions This affect auto configure feature.
            self.device_list[device_id]["localtuya_note"] = str(query_props[1])

        if device_data:
            self.device_list[device_id]["dps_data"] = device_data
            self.cached_device_list.update({device_id: self.device_list[device_id]})

        return device_data

    async def async_connect(self):
        """Connect to cloudAPI"""
        if (res := await self.async_get_access_token()) and res != "ok":
            self._logger.error("Cloud API connection failed: %s", res)
            return "authentication_failed", res
        if res and (res := await self.async_get_devices_list()) and res != "ok":
            self._logger.error("Cloud API connection failed: %s", res)
            return "device_list_failed", res
        if res:
            self._logger.info("Cloud API connection succeeded.")
        return True, res

    @property
    def token_validate(self):
        """Return whether token is expired or not"""
        cur_time = int(time.time())
        expire_time = self._token_expire_time - 30

        return expire_time >= cur_time
