"""Class to perform requests to Tuya Cloud APIs."""
import functools
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import quote

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
        self.device_list = {}
        self.device_details = {}
        self.device_specifications = {}
        self.device_shadow_properties = {}
        self.device_models = {}
        self.device_metadata_errors = {}

    def generate_payload(
        self, method, timestamp, url, headers, body=None, access_token=None
    ):
        """Generate signed payload for requests."""
        if access_token is None:
            access_token = self._access_token
        payload = self._client_id + access_token + timestamp

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

    async def async_make_request(
        self, method, url, body=None, headers=None, include_access_token=True
    ):
        """Perform requests."""
        headers = headers or {}
        timestamp = str(int(time.time() * 1000))
        access_token = self._access_token if include_access_token else ""
        payload = self.generate_payload(
            method, timestamp, url, headers, body, access_token=access_token
        )
        default_par = {
            "client_id": self._client_id,
            "access_token": access_token,
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

    async def _async_request_json(self, method, url, body=None):
        """Perform a Tuya API request and return parsed JSON or an error string."""
        try:
            resp = await self.async_make_request(method, url, body=body)
        except requests.exceptions.ConnectionError:
            return None, "Request failed, status ConnectionError"

        if not resp.ok:
            return None, "Request failed, status " + str(resp.status_code)

        r_json = resp.json()
        if not r_json["success"]:
            status = f"Error {r_json['code']}: {r_json['msg']}"
            if self._is_token_invalid(status):
                token_status = await self.async_get_access_token()
                if token_status != "ok":
                    return None, token_status

                try:
                    resp = await self.async_make_request(method, url, body=body)
                except requests.exceptions.ConnectionError:
                    return None, "Request failed, status ConnectionError"

                if not resp.ok:
                    return None, "Request failed, status " + str(resp.status_code)

                r_json = resp.json()
                if not r_json["success"]:
                    return None, f"Error {r_json['code']}: {r_json['msg']}"
            else:
                return None, status

        return r_json, "ok"

    @staticmethod
    def _is_token_invalid(status):
        """Return whether a Tuya Cloud error indicates an expired token."""
        return bool(status) and ("1010" in status or "token invalid" in status.lower())

    async def async_get_access_token(self):
        """Obtain a valid access token."""
        try:
            resp = await self.async_make_request(
                "GET", "/v1.0/token?grant_type=1", include_access_token=False
            )
        except requests.exceptions.ConnectionError:
            return "Request failed, status ConnectionError"

        if not resp.ok:
            return "Request failed, status " + str(resp.status_code)

        r_json = resp.json()
        if not r_json["success"]:
            return f"Error {r_json['code']}: {r_json['msg']}"

        self._access_token = resp.json()["result"]["access_token"]
        return "ok"

    async def async_get_devices_list(self):
        """Obtain the list of devices associated to a user."""
        r_json, status = await self._async_request_json(
            "GET", f"/v1.0/users/{self._user_id}/devices"
        )
        if status != "ok":
            return status

        self.device_list = {dev["id"]: dev for dev in r_json["result"]}
        # _LOGGER.debug("DEV_LIST: %s", self.device_list)

        return "ok"

    async def async_get_device_details_bulk(self, device_ids):
        """Obtain detailed cloud metadata for up to 20 devices at a time."""
        if not device_ids:
            return "ok"

        for start in range(0, len(device_ids), 20):
            batch = device_ids[start : start + 20]
            encoded_ids = quote(",".join(batch), safe=",")
            r_json, status = await self._async_request_json(
                "GET", f"/v2.0/cloud/thing/batch?device_ids={encoded_ids}"
            )
            if status != "ok":
                for dev_id in batch:
                    self.device_metadata_errors.setdefault(dev_id, []).append(status)
                return status

            for device in r_json.get("result", []):
                dev_id = device.get("id")
                if not dev_id:
                    continue
                self.device_details[dev_id] = device
                self.device_list.setdefault(dev_id, {}).update(device)

        return "ok"

    async def async_get_device_specifications(self, device_id):
        """Obtain a device's instruction and status set from Tuya Cloud."""
        r_json, status = await self._async_request_json(
            "GET", f"/v1.0/devices/{device_id}/specifications"
        )
        if status != "ok":
            self.device_metadata_errors.setdefault(device_id, []).append(status)
            return status

        self.device_specifications[device_id] = r_json.get("result", {})
        return "ok"

    async def async_get_device_shadow_properties(self, device_id):
        """Obtain a device's cloud shadow properties, including code to DP id data."""
        r_json, status = await self._async_request_json(
            "GET", f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        )
        if status != "ok":
            self.device_metadata_errors.setdefault(device_id, []).append(status)
            return status

        result = r_json.get("result") or {}
        self.device_shadow_properties[device_id] = result.get("properties", [])
        return "ok"

    async def async_get_device_model(self, device_id):
        """Obtain a device's full thing model, including custom DP enum ranges."""
        r_json, status = await self._async_request_json(
            "GET", f"/v2.0/cloud/thing/{device_id}/model"
        )
        if status != "ok":
            self.device_metadata_errors.setdefault(device_id, []).append(status)
            return status

        result = r_json.get("result") or {}
        model = result.get("model", {})
        if isinstance(model, str):
            try:
                model = json.loads(model)
            except (TypeError, ValueError):
                model = {}
        self.device_models[device_id] = model if isinstance(model, dict) else {}
        return "ok"

    async def async_enrich_devices(self, device_ids=None):
        """Fetch richer metadata used by automatic device import."""
        if device_ids is None:
            device_ids = list(self.device_list)
        device_ids = [dev_id for dev_id in device_ids if dev_id]
        self.device_metadata_errors = {
            dev_id: errors
            for dev_id, errors in self.device_metadata_errors.items()
            if dev_id not in device_ids
        }

        details_status = await self.async_get_device_details_bulk(device_ids)
        for dev_id in device_ids:
            await self.async_get_device_specifications(dev_id)
            await self.async_get_device_shadow_properties(dev_id)
            await self.async_get_device_model(dev_id)

        return details_status

    def metadata_for(self, device_id):
        """Return all known cloud metadata for a device."""
        return {
            "device": self.device_list.get(device_id, {}),
            "details": self.device_details.get(device_id, {}),
            "specifications": self.device_specifications.get(device_id, {}),
            "shadow_properties": self.device_shadow_properties.get(device_id, []),
            "model": self.device_models.get(device_id, {}),
            "errors": self.device_metadata_errors.get(device_id, []),
        }
