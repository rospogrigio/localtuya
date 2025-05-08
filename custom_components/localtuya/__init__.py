"""The LocalTuya integration."""
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_HOST,
    CONF_ID,
    CONF_PLATFORM,
    CONF_REGION,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    SERVICE_RELOAD,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval

from .cloud_api import TuyaCloudApi
from .common import TuyaDevice, async_config_entry_by_device_id
from .config_flow import ENTRIES_VERSION, config_schema
from .const import (
    ATTR_UPDATED_AT,
    CONF_NO_CLOUD,
    CONF_PRODUCT_KEY,
    CONF_USER_ID,
    DATA_CLOUD,
    DATA_DISCOVERY,
    DOMAIN,
    TUYA_DEVICES,
)
from .discovery import TuyaDiscovery

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"

RECONNECT_INTERVAL = timedelta(seconds=60)

CONFIG_SCHEMA = config_schema()

CONF_DP = "dp"
CONF_VALUE = "value"

SERVICE_SET_DP = "set_dp"
SERVICE_SET_DP_SCHEMA = vol.Schema({
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_DP): int,
    vol.Required(CONF_VALUE): object,
})


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the LocalTuya integration component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][TUYA_DEVICES] = {}

    device_cache: dict[str, str] = {}

    async def _handle_reload(call: Any) -> None:
        """Handle reload service call."""
        _LOGGER.info("Service %s.reload called: reloading integration", DOMAIN)
        current_entries = hass.config_entries.async_entries(DOMAIN)
        await asyncio.gather(
            *(hass.config_entries.async_reload(entry.entry_id) for entry in current_entries)
        )

    async def _handle_set_dp(call: Any) -> None:
        """Handle set_dp service call."""
        dev_id = call.data[CONF_DEVICE_ID]
        if dev_id not in hass.data[DOMAIN][TUYA_DEVICES]:
            raise HomeAssistantError(f"Unknown device ID {dev_id}")

        device: TuyaDevice = hass.data[DOMAIN][TUYA_DEVICES][dev_id]
        if not device.connected:
            raise HomeAssistantError("Device not connected")

        await device.set_dp(call.data[CONF_VALUE], call.data[CONF_DP])

    def _device_discovered(device: dict[str, Any]) -> None:
        """Update device address if it changed."""
        device_ip = device["ip"]
        device_id = device["gwId"]
        product_key = device["productKey"]

        entry = async_config_entry_by_device_id(hass, device_id)
        if not entry:
            return

        if device_id not in device_cache:
            if entry and device_id in entry.data.get(CONF_DEVICES, {}):
                device_cache[device_id] = entry.data[CONF_DEVICES][device_id][CONF_HOST]

        if device_id not in device_cache:
            return

        dev_entry = entry.data[CONF_DEVICES][device_id]
        updated = False
        new_data = entry.data.copy()

        if device_cache[device_id] != device_ip:
            updated = True
            new_data[CONF_DEVICES][device_id][CONF_HOST] = device_ip
            device_cache[device_id] = device_ip

        if dev_entry.get(CONF_PRODUCT_KEY) != product_key:
            updated = True
            new_data[CONF_DEVICES][device_id][CONF_PRODUCT_KEY] = product_key

        if updated:
            _LOGGER.debug("Updating keys for device %s: %s %s", device_id, device_ip, product_key)
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            hass.config_entries.async_update_entry(entry, data=new_data)

        elif device_id in hass.data[DOMAIN][TUYA_DEVICES]:
            _LOGGER.debug("Device %s found with IP %s", device_id, device_ip)

        dev = hass.data[DOMAIN][TUYA_DEVICES].get(device_id)
        if dev and not dev.connected:
            dev.async_connect()

    async def _async_reconnect(_: Any) -> None:
        """Reconnect devices not connected."""
        for device in hass.data[DOMAIN][TUYA_DEVICES].values():
            if not device.connected:
                device.async_connect()

    async_track_time_interval(hass, _async_reconnect, RECONNECT_INTERVAL)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DP,
        _handle_set_dp,
        schema=SERVICE_SET_DP_SCHEMA,
    )

    discovery = TuyaDiscovery(_device_discovered)

    async def _shutdown(_: Any) -> None:
        """Shutdown discovery on Home Assistant stop."""
        discovery.close()

    try:
        await discovery.start()
        hass.data[DOMAIN][DATA_DISCOVERY] = discovery
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown)
    except Exception as e:
        _LOGGER.exception("Failed to set up discovery: %s", str(e))

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entries merging all of them in one."""
    new_version = ENTRIES_VERSION
    stored_entries = hass.config_entries.async_entries(DOMAIN)

    if config_entry.version == 1:
        _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

        if config_entry.entry_id == stored_entries[0].entry_id:
            new_data = {
                CONF_REGION: "eu",  # Still hardcoded
                CONF_CLIENT_ID: "",
                CONF_CLIENT_SECRET: "",
                CONF_USER_ID: "",
                CONF_USERNAME: DOMAIN,
                CONF_NO_CLOUD: True,
                CONF_DEVICES: {config_entry.data[CONF_DEVICE_ID]: config_entry.data.copy()},
                ATTR_UPDATED_AT: str(int(time.time() * 1000)),
            }
            config_entry.version = new_version
            hass.config_entries.async_update_entry(config_entry, title=DOMAIN, data=new_data)
        else:
            new_data = stored_entries[0].data.copy()
            new_data[CONF_DEVICES].update(
                {config_entry.data[CONF_DEVICE_ID]: config_entry.data.copy()}
            )
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            hass.config_entries.async_update_entry(stored_entries[0], data=new_data)
            await hass.config_entries.async_remove(config_entry.entry_id)

    _LOGGER.info(
        "Entry %s successfully migrated to version %s.",
        config_entry.entry_id,
        new_version,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LocalTuya integration from a config entry."""
    if entry.version < ENTRIES_VERSION:
        _LOGGER.debug(
            "Skipping setup for entry %s because version (%s) is old",
            entry.entry_id,
            entry.version,
        )
        return False

    region = entry.data[CONF_REGION]
    client_id = entry.data[CONF_CLIENT_ID]
    secret = entry.data[CONF_CLIENT_SECRET]
    user_id = entry.data[CONF_USER_ID]
    no_cloud = entry.data.get(CONF_NO_CLOUD, True)

    tuya_api = TuyaCloudApi(hass, region, client_id, secret, user_id)
    hass.data[DOMAIN][DATA_CLOUD] = tuya_api

    if not no_cloud:
        res = await tuya_api.async_get_access_token()
        if res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
        else:
            _LOGGER.info("Cloud API connection succeeded.")
            await tuya_api.async_get_devices_list()
    else:
        _LOGGER.info("Cloud API account not configured.")
        await asyncio.sleep(1)

    async def setup_entities(device_ids: list[str]) -> None:
        platforms = set()
        for dev_id in device_ids:
            entities = entry.data[CONF_DEVICES][dev_id][CONF_ENTITIES]
            platforms.update(entity[CONF_PLATFORM] for entity in entities)
            hass.data[DOMAIN][TUYA_DEVICES][dev_id] = TuyaDevice(hass, entry, dev_id)

        await hass.config_entries.async_forward_entry_setups(entry, platforms)

        for dev_id in device_ids:
            hass.data[DOMAIN][TUYA_DEVICES][dev_id].async_connect()

        await async_remove_orphan_entities(hass, entry)

    hass.async_create_task(setup_entities(list(entry.data[CONF_DEVICES].keys())))

    unsub_listener = entry.add_update_listener(update_listener)
    hass.data[DOMAIN][entry.entry_id] = {UNSUB_LISTENER: unsub_listener}

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = {entity[CONF_PLATFORM] for dev in entry.data[CONF_DEVICES].values()
                 for entity in dev[CONF_ENTITIES]}

    unload_ok = all(
        await asyncio.gather(
            *(hass.config_entries.async_forward_entry_unload(entry, platform) for platform in platforms)
        )
    )

    hass.data[DOMAIN][entry.entry_id][UNSUB_LISTENER]()
    for device in hass.data[DOMAIN][TUYA_DEVICES].values():
        if device.connected:
            await device.close()

    if unload_ok:
        hass.data[DOMAIN][TUYA_DEVICES] = {}

    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    dev_id = list(device_entry.identifiers)[0][1].split("_")[-1]

    ent_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id):
        if dev_id in entity.unique_id:
            ent_reg.async_remove(entity.entity_id)

    if dev_id not in config_entry.data[CONF_DEVICES]:
        _LOGGER.info("Device %s not found in config entry: assuming removed.", dev_id)
        return True

    await hass.data[DOMAIN][TUYA_DEVICES][dev_id].close()

    new_data = config_entry.data.copy()
    new_data[CONF_DEVICES].pop(dev_id)
    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
    hass.config_entries.async_update_entry(config_entry, data=new_data)

    _LOGGER.info("Device %s removed.", dev_id)

    return True


async def async_remove_orphan_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove orphan entities for a config entry."""
    pass
