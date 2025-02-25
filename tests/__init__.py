"""Init localtuya tests"""

import asyncio
import homeassistant.util.ulid as ulid_util
import os, sys
import pytest
import threading
import time

from typing import Any
from unittest.mock import AsyncMock, Mock
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.localtuya import TuyaCloudApi
from custom_components.localtuya import coordinator
from custom_components.localtuya import entity
from custom_components.localtuya.const import DOMAIN

HOST = "192.168.1.100"
DEVICE_NAME = "device"

DEVICE_CONFIG = {
    "host": HOST,
    "device_id": "767823809c9c1f458745",
    "protocol_version": "3.3",
    "local_key": "wV[NcWGUSFF`dSgO",
    "friendly_name": "Local 3G",
}


async def init(config: dict[str, dict[str, Any]], entity_domain, entity_class):
    add_entities = AsyncMock()

    asyncio.create_task = lambda _: None
    asyncio.get_running_loop = lambda: type(
        "", (), {"_thread_id": threading.get_ident()}
    )
    hass = HomeAssistant("")
    entry = ConfigEntry(**create_entry(config))
    tuya_api = TuyaCloudApi("EU", "test_client_id", "test_secret", "test_user_id")

    hass.data.setdefault("localtuya", {entry.entry_id: {}})

    dump_device = coordinator.TuyaDevice(hass, entry, config[DEVICE_NAME])
    dump_device.status_updated = lambda x: [
        [e._status.update(x), e.connection_made(), e.status_updated()]
        for e in get_entites(dump_device)
    ]

    localtuya_hass_data = coordinator.HassLocalTuyaData(tuya_api, {HOST: dump_device})
    hass.data[DOMAIN][entry.entry_id] = localtuya_hass_data

    await entity.async_setup_entry(
        entity_domain,
        entity_class,
        lambda _: {},
        hass=hass,
        config_entry=entry,
        async_add_entities=add_entities,
    )

    add_entities.assert_called_once()
    return dump_device


def create_entry(config: dict[str, dict[str, Any]]):
    return {
        "data": {"devices": config},
        "disabled_by": None,
        "discovery_keys": None,
        "domain": "test",
        "entry_id": ulid_util.ulid_now(),
        "minor_version": 1,
        "options": {},
        "pref_disable_new_entities": None,
        "pref_disable_polling": None,
        "title": "Mock LocalTuya",
        "unique_id": None,
        "version": 1,
        "source": "user",
    }


def get_entites(device: coordinator.TuyaDevice):
    return getattr(device, "_entities")
