"""Diagnostics support for LocalTuya."""

from __future__ import annotations

import copy
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_DEVICES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import HassLocalTuyaData
from .const import CONF_LOCAL_KEY, CONF_USER_ID, DOMAIN

CLOUD_DEVICES = "cloud_devices"
DEVICE_CONFIG = "device_config"
DEVICE_CLOUD_INFO = "device_cloud_info"

_LOGGER = logging.getLogger(__name__)

DATA_OBFUSCATE = {"ip": 1, "uid": 3, CONF_LOCAL_KEY: 3, "lat": 0, "lon": 0}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {}
    data = dict(entry.data)
    hass_localtuya: HassLocalTuyaData = hass.data[DOMAIN][entry.entry_id]
    tuya_api = hass_localtuya.cloud_data
    # censoring private information on integration diagnostic data
    for field in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
        data[field] = obfuscate(data[field])
    data[CONF_DEVICES] = copy.deepcopy(entry.data[CONF_DEVICES])
    for dev_id, dev in data[CONF_DEVICES].items():
        local_key = dev[CONF_LOCAL_KEY]
        local_key_obfuscated = obfuscate(local_key)
        dev[CONF_LOCAL_KEY] = local_key_obfuscated
    data[CLOUD_DEVICES] = copy.deepcopy(tuya_api.device_list)
    for dev_id, dev in data[CLOUD_DEVICES].items():
        for obf, obf_len in DATA_OBFUSCATE.items():
            if ob := data[CLOUD_DEVICES][dev_id].get(obf):
                data[CLOUD_DEVICES][dev_id][obf] = obfuscate(ob, obf_len, obf_len)
    return data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    data = {}
    dev_id = list(device.identifiers)[0][1].split("_")[-1]
    data[DEVICE_CONFIG] = entry.data[CONF_DEVICES][dev_id].copy()
    # NOT censoring private information on device diagnostic data
    # local_key = data[DEVICE_CONFIG][CONF_LOCAL_KEY]
    # data[DEVICE_CONFIG][CONF_LOCAL_KEY] = f"{local_key[0:3]}...{local_key[-3:]}"

    hass_localtuya: HassLocalTuyaData = hass.data[DOMAIN][entry.entry_id]
    tuya_api = hass_localtuya.cloud_data
    if dev_id in tuya_api.device_list:
        data[DEVICE_CLOUD_INFO] = copy.deepcopy(tuya_api.device_list[dev_id])
        for obf, obf_len in DATA_OBFUSCATE.items():
            if ob := data[DEVICE_CLOUD_INFO].get(obf):
                data[DEVICE_CLOUD_INFO][obf] = obfuscate(ob, obf_len, obf_len)
        # NOT censoring private information on device diagnostic data
        # local_key = data[DEVICE_CLOUD_INFO][CONF_LOCAL_KEY]
        # local_key_obfuscated = "{local_key[0:3]}...{local_key[-3:]}"
        # data[DEVICE_CLOUD_INFO][CONF_LOCAL_KEY] = local_key_obfuscated

    # data["log"] = hass.data[DOMAIN][CONF_DEVICES][dev_id].logger.retrieve_log()
    return data


def obfuscate(key, start_characters=3, end_characters=3) -> str:
    """Return obfuscated text by removing characters between [start_characters and end_characters]"""
    if start_characters <= 0 and end_characters <= 0:
        return ""

    return f"{key[0:start_characters]}...{key[-end_characters:]}"
