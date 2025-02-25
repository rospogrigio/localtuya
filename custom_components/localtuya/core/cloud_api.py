"""Class to perform requests to Tuya Cloud APIs."""

import aiohttp
import asyncio
import hashlib
import hmac
import json
import logging
import time


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


class AioHttpSession:
    """
    A class to manage a shared aiohttp.ClientSession.
    Ensures that only one session is created, based on active usage counts.
    """

    _session: aiohttp.ClientSession = None
    _lock = asyncio.Lock()
    _active_requests = 0

    async def __get_session(self):
        """
        Create ClientSession if it doesn't exist yet.
        Increases the active requests to keep track of current session uses.

        Returns: aiohttp.ClientSession
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
        self._active_requests += 1
        return self._session

    async def __close_session(self):
        """Close session only if this is the last used of session."""
        self._active_requests -= 1

        async with self._lock:
            if self._session and self._active_requests <= 0:
                await self._session.close()
                self._session = None

    async def __aenter__(self):
        return await self.__get_session()

    async def __aexit__(self, exc_type, exc, tb):
        await self.__close_session()


class TuyaCloudApi:
    """Class to send API calls."""

    def __init__(self, region_code, client_id, secret, user_id):
        """Initialize the class."""
        self._logger = CustomAdapter(
            logging.getLogger(__name__), {"prefix": user_id[:3] + "..." + user_id[-3:]}
        )

        self._session = AioHttpSession()
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

        async with self._session as session:
            try:
                if method == "GET":
                    async with session.get(
                        full_url, headers=dict(default_par, **headers)
                    ) as resp:
                        return await resp.json()

                if method == "POST":
                    async with session.post(
                        full_url,
                        headers=dict(default_par, **headers),
                        data=json.dumps(body),
                    ) as resp:
                        return await resp.json()

                if method == "PUT":
                    async with session.put(
                        full_url,
                        headers=dict(default_par, **headers),
                        data=json.dumps(body),
                    ) as resp:
                        return await resp.json()
            except (aiohttp.ClientConnectionError, TimeoutError) as ex:
                self._logger.debug(f"Failed to send request to tuya cloud: {ex}")
                return False

    async def async_get_access_token(self) -> str | None:
        """Obtain a valid access token."""
        # Reset access token
        self._token_expire_time = -1
        self._access_token = ""

        if not (
            resp := await self.async_make_request("GET", "/v1.0/token?grant_type=1")
        ):
            self._token_expire_time = 0
            return self._logger.debug(f"Failed to retrieve a valid token")

        if not resp["success"]:
            self._token_expire_time = 0
            return f"Error {resp['code']}: {resp['msg']}"

        req_results = resp["result"]

        expire_time = int(req_results.get("expire_time", 3600))
        self._token_expire_time = int(time.time()) + expire_time
        self._access_token = resp["result"]["access_token"]
        return "ok"

    async def async_get_devices_list(self, force_update=False) -> str | None:
        """Obtain the list of devices associated to a user. - force_update will ignore last update check."""
        interval = (
            DEVICES_UPDATE_INTERVAL_FORCED if force_update else DEVICES_UPDATE_INTERVAL
        )
        if (
            self.device_list
            and int(time.time()) - (self._last_devices_update + interval) < 0
        ):
            return self._logger.debug(f"Devices has been updated a minutes ago.")

        if not (
            resp := await self.async_make_request(
                "GET", url=f"/v1.0/users/{self._user_id}/devices"
            )
        ):
            return self._logger.debug(f"Failed to retrieve a devices list")

        if not resp["success"]:
            return f"Error {resp['code']}: {resp['msg']}"

        self.device_list.update({dev["id"]: dev for dev in resp["result"]})

        self._last_devices_update = int(time.time())
        return "ok"

    async def async_get_devices_dps_query(self):
        """Update All the devices dps_data."""
        # Get Devices DPS Data.
        await asyncio.wait(
            asyncio.create_task(self.async_get_device_functions(devid))
            for devid in self.device_list
        )
        return "ok"

    async def async_get_device_specifications(self, device_id) -> dict[str, dict]:
        """Obtain the DP ID mappings for a device."""

        if not (
            resp := await self.async_make_request(
                "GET", url=f"/v1.1/devices/{device_id}/specifications"
            )
        ):
            return self._logger.debug(f"Failed to retrieve a device specifications")

        if not resp["success"]:
            return {}, f"Error {resp['code']}: {resp['msg']}"

        return resp["result"], "ok"

    async def async_get_device_query_properties(self, device_id) -> dict[dict, str]:
        """Obtain the DP ID mappings for a device correctly! Note: This won't works if the subscription expired."""

        if not (
            resp := await self.async_make_request(
                "GET", url=f"/v2.0/cloud/thing/{device_id}/shadow/properties"
            )
        ):
            return self._logger.debug(f"Failed to retrieve a device properties")

        if not resp["success"]:
            return {}, f"Error {resp['code']}: {resp['msg']}"

        return resp["result"], "ok"

    async def async_get_device_query_things_data_model(
        self, device_id
    ) -> dict[str, dict]:
        """Obtain the DP ID mappings for a device."""

        if not (
            resp := await self.async_make_request(
                "GET", url=f"/v2.0/cloud/thing/{device_id}/model"
            )
        ):
            return self._logger.debug(f"Failed to retrieve a device data model")

        if not resp["success"]:
            return {}, f"Error {resp['code']}: {resp['msg']}"

        return resp["result"], "ok"

    async def async_get_device_functions(self, device_id) -> dict[str, dict]:
        """Pull Devices Properties and Specifications to devices_list"""
        cached = device_id in self.cached_device_list
        if cached and (dps_data := self.cached_device_list[device_id].get("dps_data")):
            self.device_list[device_id]["dps_data"] = dps_data
            return dps_data

        device_data = {}
        get_data = [
            self.async_get_device_specifications(device_id),
            self.async_get_device_query_properties(device_id),
            self.async_get_device_query_things_data_model(device_id),
        ]
        try:
            specs, query_props, query_model = await asyncio.gather(*get_data)
        except (Exception,) as ex:
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
            self._logger.warning("Cloud API connection failed: %s", res)
            return "authentication_failed", res
        if res and (res := await self.async_get_devices_list()) and res != "ok":
            self._logger.warning("Cloud API connection failed: %s", res)
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
