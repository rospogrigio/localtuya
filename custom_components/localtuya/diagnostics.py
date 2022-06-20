"""Diagnostics support for LocalTuya."""
from __future__ import annotations

import copy
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_DEVICES
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import CONF_LOCAL_KEY, CONF_USER_ID, DATA_CLOUD, DOMAIN

CLOUD_DEVICES = "cloud_devices"
DEVICE_CONFIG = "device_config"
DEVICE_CLOUD_INFO = "device_cloud_info"

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {}
    data = dict(entry.data)
    tuya_api = hass.data[DOMAIN][DATA_CLOUD]
    # censoring private information on integration diagnostic data
    for field in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
        data[field] = f"{data[field][0:3]}...{data[field][-3:]}"
    data[CONF_DEVICES] = copy.deepcopy(entry.data[CONF_DEVICES])
    for dev_id, dev in data[CONF_DEVICES].items():
        local_key = dev[CONF_LOCAL_KEY]
        local_key_obfuscated = f"{local_key[0:3]}...{local_key[-3:]}"
        dev[CONF_LOCAL_KEY] = local_key_obfuscated
    data[CLOUD_DEVICES] = tuya_api.device_list
    for dev_id, dev in data[CLOUD_DEVICES].items():
        local_key = data[CLOUD_DEVICES][dev_id][CONF_LOCAL_KEY]
        local_key_obfuscated = f"{local_key[0:3]}...{local_key[-3:]}"
        data[CLOUD_DEVICES][dev_id][CONF_LOCAL_KEY] = local_key_obfuscated
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

    tuya_api = hass.data[DOMAIN][DATA_CLOUD]
    if dev_id in tuya_api.device_list:
        data[DEVICE_CLOUD_INFO] = tuya_api.device_list[dev_id]
        # NOT censoring private information on device diagnostic data
        # local_key = data[DEVICE_CLOUD_INFO][CONF_LOCAL_KEY]
        # local_key_obfuscated = "{local_key[0:3]}...{local_key[-3:]}"
        # data[DEVICE_CLOUD_INFO][CONF_LOCAL_KEY] = local_key_obfuscated

    # data["log"] = hass.data[DOMAIN][CONF_DEVICES][dev_id].logger.retrieve_log()
    return data
