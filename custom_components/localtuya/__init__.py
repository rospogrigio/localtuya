"""The LocalTuya integration."""
import asyncio
import logging
import time
from collections.abc import Mapping
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
import voluptuous as vol
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
from homeassistant.helpers.service import async_register_admin_service

from .cloud_api import TuyaCloudApi
from .common import TuyaDevice, async_config_entry_by_device_id
from .config_flow import (
    ENTRIES_VERSION,
    config_schema,
    CannotConnect,
    EmptyDpsList,
    InvalidAuth,
)
from .auto_sync import async_auto_import_devices
from .const import (
    ATTR_UPDATED_AT,
    CONF_LOCAL_KEY,
    CONF_NO_CLOUD,
    CONF_PRODUCT_KEY,
    CONF_PRODUCT_NAME,
    CONF_USER_ID,
    DATA_CLOUD,
    DATA_DISCOVERY,
    DOMAIN,
    TUYA_DEVICES,
)
from .discovery import TuyaDiscovery

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"
ENTRY_DATA_SNAPSHOT = "entry_data_snapshot"

RECONNECT_INTERVAL = timedelta(seconds=60)
AUTO_SYNC_INTERVAL = timedelta(hours=1)

CONFIG_SCHEMA = config_schema()

CONF_DP = "dp"
CONF_VALUE = "value"

SERVICE_SET_DP = "set_dp"
SERVICE_SET_DP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_DP): int,
        vol.Required(CONF_VALUE): object,
    }
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][TUYA_DEVICES] = {}

    device_cache = {}

    async def _handle_reload(service):
        """Handle reload service call."""
        _LOGGER.info("Service %s.reload called: reloading integration", DOMAIN)

        current_entries = hass.config_entries.async_entries(DOMAIN)

        reload_tasks = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in current_entries
        ]

        results = await asyncio.gather(*reload_tasks, return_exceptions=True)
        if any(isinstance(result, Exception) for result in results):
            _LOGGER.warning(
                "Config entry reload failed; forcing LocalTuya runtime reconnect"
            )
            await _async_force_reconnect_devices()

    async def _async_force_reconnect_devices():
        """Force all runtime devices to reconnect without unloading entities."""
        reconnect_tasks = [
            device.async_reconnect()
            for device in list(hass.data[DOMAIN][TUYA_DEVICES].values())
        ]
        if reconnect_tasks:
            await asyncio.gather(*reconnect_tasks)

    async def _handle_set_dp(event):
        """Handle set_dp service call."""
        dev_id = event.data[CONF_DEVICE_ID]
        if dev_id not in hass.data[DOMAIN][TUYA_DEVICES]:
            raise HomeAssistantError("unknown device id")

        device = hass.data[DOMAIN][TUYA_DEVICES][dev_id]
        if not device.connected:
            raise HomeAssistantError("not connected to device")

        await device.set_dp(event.data[CONF_VALUE], event.data[CONF_DP])

    def _device_discovered(device):
        """Update address of device if it has changed."""
        device_ip = device["ip"]
        device_id = device["gwId"]
        product_key = device.get("productKey")

        # If device is not in cache, check if a config entry exists
        entry = async_config_entry_by_device_id(hass, device_id)
        if entry is None:
            return

        if device_id not in device_cache:
            if entry and device_id in entry.data[CONF_DEVICES]:
                # Save address from config entry in cache to trigger
                # potential update below
                host_ip = entry.data[CONF_DEVICES][device_id][CONF_HOST]
                device_cache[device_id] = host_ip

        if device_id not in device_cache:
            return

        dev_entry = entry.data[CONF_DEVICES][device_id]

        new_data = _copy_config_data(entry.data)
        updated = False

        if device_cache[device_id] != device_ip:
            updated = True
            new_data[CONF_DEVICES][device_id][CONF_HOST] = device_ip
            device_cache[device_id] = device_ip

        if product_key and dev_entry.get(CONF_PRODUCT_KEY) != product_key:
            updated = True
            new_data[CONF_DEVICES][device_id][CONF_PRODUCT_KEY] = product_key

        runtime_device = hass.data[DOMAIN][TUYA_DEVICES].get(device_id)

        # Update settings if something changed, otherwise try to connect. Updating
        # settings now applies runtime-safe fields in-place so IP churn does not
        # require a full config reload before the live object can recover.
        if updated:
            _LOGGER.debug(
                "Updating keys for device %s: %s %s", device_id, device_ip, product_key
            )
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            hass.config_entries.async_update_entry(entry, data=new_data)
            if runtime_device:
                runtime_device.update_config(new_data[CONF_DEVICES][device_id])
                if not runtime_device.connected:
                    runtime_device.async_connect(force=True)

        elif device_id in hass.data[DOMAIN][TUYA_DEVICES]:
            _LOGGER.debug("Device %s found with IP %s", device_id, device_ip)

        if not runtime_device:
            _LOGGER.debug(
                "Discovered device %s before runtime device was ready", device_id
            )
        elif not runtime_device.connected:
            runtime_device.async_connect(force=True)


    def _shutdown(event):
        """Clean up resources when shutting down."""
        discovery.close()

    async def _async_reconnect(now):
        """Try connecting to devices not already connected to."""
        for device_id, device in hass.data[DOMAIN][TUYA_DEVICES].items():
            if not device.connected:
                device.async_connect()

    async_track_time_interval(hass, _async_reconnect, RECONNECT_INTERVAL)

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    hass.services.async_register(
        DOMAIN, SERVICE_SET_DP, _handle_set_dp, schema=SERVICE_SET_DP_SCHEMA
    )

    discovery = TuyaDiscovery(_device_discovered)
    try:
        await discovery.start()
        hass.data[DOMAIN][DATA_DISCOVERY] = discovery
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("failed to set up discovery")

    return True


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entries merging all of them in one."""
    new_version = ENTRIES_VERSION
    stored_entries = hass.config_entries.async_entries(DOMAIN)
    if config_entry.version == 1:
        _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

        if config_entry.entry_id == stored_entries[0].entry_id:
            _LOGGER.debug(
                "Migrating the first config entry (%s)", config_entry.entry_id
            )
            new_data = {}
            new_data[CONF_REGION] = "eu"
            new_data[CONF_CLIENT_ID] = ""
            new_data[CONF_CLIENT_SECRET] = ""
            new_data[CONF_USER_ID] = ""
            new_data[CONF_USERNAME] = DOMAIN
            new_data[CONF_NO_CLOUD] = True
            new_data[CONF_DEVICES] = {
                config_entry.data[CONF_DEVICE_ID]: config_entry.data.copy()
            }
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            config_entry.version = new_version
            hass.config_entries.async_update_entry(
                config_entry, title=DOMAIN, data=new_data
            )
        else:
            _LOGGER.debug(
                "Merging the config entry %s into the main one", config_entry.entry_id
            )
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    if entry.version < ENTRIES_VERSION:
        _LOGGER.debug(
            "Skipping setup for entry %s since its version (%s) is old",
            entry.entry_id,
            entry.version,
        )
        return

    region = entry.data[CONF_REGION]
    client_id = entry.data[CONF_CLIENT_ID]
    secret = entry.data[CONF_CLIENT_SECRET]
    user_id = entry.data[CONF_USER_ID]
    tuya_api = TuyaCloudApi(hass, region, client_id, secret, user_id)
    no_cloud = True
    if CONF_NO_CLOUD in entry.data:
        no_cloud = entry.data.get(CONF_NO_CLOUD)
    if no_cloud:
        _LOGGER.info("Cloud API account not configured.")
        # wait 1 second to make sure possible migration has finished
        await asyncio.sleep(1)
    else:
        res = await tuya_api.async_get_access_token()
        if res != "ok":
            _LOGGER.error("Cloud API connection failed: %s", res)
        else:
            _LOGGER.info("Cloud API connection succeeded.")
            res = await tuya_api.async_get_devices_list()
    hass.data[DOMAIN][DATA_CLOUD] = tuya_api

    platforms = set()
    for dev_id in entry.data[CONF_DEVICES].keys():
        entities = entry.data[CONF_DEVICES][dev_id][CONF_ENTITIES]
        platforms = platforms.union(
            set(entity[CONF_PLATFORM] for entity in entities)
        )
        hass.data[DOMAIN][TUYA_DEVICES][dev_id] = TuyaDevice(hass, entry, dev_id)

    await async_remove_orphan_entities(hass, entry)

    # Setup all platforms at once, letting HA handling each platform and avoiding
    # potential integration restarts while elements are still initialising.
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    async def setup_entities(device_ids):
        for dev_id in device_ids:
            hass.data[DOMAIN][TUYA_DEVICES][dev_id].async_connect()

        await async_remove_orphan_entities(hass, entry)

    hass.async_create_task(setup_entities(entry.data[CONF_DEVICES].keys()))

    async def _async_cloud_auto_sync(now):
        if entry.data.get(CONF_NO_CLOUD):
            return
        res = await tuya_api.async_get_devices_list()
        if res != "ok" and ("1010" in res or "token invalid" in res.lower()):
            token_res = await tuya_api.async_get_access_token()
            if token_res == "ok":
                res = await tuya_api.async_get_devices_list()
        if res != "ok":
            _LOGGER.warning("Cloud auto-sync skipped: %s", res)
            return
        try:
            sync_result = await async_auto_import_devices(
                hass,
                entry,
                tuya_api,
                remove_missing=False,
                detect_available_dps=None,
                cannot_connect=CannotConnect,
                invalid_auth=InvalidAuth,
                empty_dps=EmptyDpsList,
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Cloud auto-sync failed")
            return
        if sync_result["imported"] or sync_result["updated"]:
            _LOGGER.info(
                "Cloud auto-sync imported %d device(s), updated %d device(s), skipped %d.",
                len(sync_result["imported"]),
                len(sync_result["updated"]),
                len(sync_result["skipped"]),
            )
            await hass.config_entries.async_reload(entry.entry_id)

    async def _async_initial_cloud_auto_sync():
        """Let HA finish setup before running cloud import/update work."""
        await asyncio.sleep(30)
        await _async_cloud_auto_sync(None)

    unsub_auto_sync = async_track_time_interval(
        hass, _async_cloud_auto_sync, AUTO_SYNC_INTERVAL
    )

    initial_auto_sync_task = None
    if not no_cloud:
        initial_auto_sync_task = hass.async_create_task(_async_initial_cloud_auto_sync())

    unsub_listener = entry.add_update_listener(update_listener)
    hass.data[DOMAIN][entry.entry_id] = {
        UNSUB_LISTENER: unsub_listener,
        "unsub_auto_sync": unsub_auto_sync,
        "initial_auto_sync_task": initial_auto_sync_task,
        ENTRY_DATA_SNAPSHOT: _copy_config_data(entry.data),
    }

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    platforms = {}

    for dev_id, dev_entry in entry.data[CONF_DEVICES].items():
        for entity in dev_entry[CONF_ENTITIES]:
            platforms[entity[CONF_PLATFORM]] = True

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in platforms
            ]
        )
    )

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_data[UNSUB_LISTENER]()
    if entry_data.get("unsub_auto_sync"):
        entry_data["unsub_auto_sync"]()
    if entry_data.get("initial_auto_sync_task"):
        entry_data["initial_auto_sync_task"].cancel()
    for dev_id, device in list(hass.data[DOMAIN][TUYA_DEVICES].items()):
        await device.close()

    if unload_ok:
        hass.data[DOMAIN][TUYA_DEVICES] = {}

    return True


async def update_listener(hass, config_entry):
    """Update listener."""
    entry_data = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
    previous_data = entry_data.get(ENTRY_DATA_SNAPSHOT)
    if previous_data is not None and not _entry_update_requires_reload(
        previous_data, config_entry.data
    ):
        _LOGGER.debug(
            "Applying runtime-safe LocalTuya config update without config reload"
        )
        _apply_runtime_device_config(hass, config_entry)
        entry_data[ENTRY_DATA_SNAPSHOT] = _copy_config_data(config_entry.data)
        return
    entry_data[ENTRY_DATA_SNAPSHOT] = _copy_config_data(config_entry.data)
    await hass.config_entries.async_reload(config_entry.entry_id)


def _entry_update_requires_reload(previous_data, current_data):
    """Return whether a config update changes entity/platform setup."""
    previous_devices = previous_data.get(CONF_DEVICES, {})
    current_devices = current_data.get(CONF_DEVICES, {})
    if set(previous_devices) != set(current_devices):
        return True

    for device_id, previous_device in previous_devices.items():
        current_device = current_devices.get(device_id, {})
        if _strip_runtime_device_fields(previous_device) != _strip_runtime_device_fields(
            current_device
        ):
            return True

    return False


def _strip_runtime_device_fields(device):
    """Remove fields that can be applied to a live TuyaDevice."""
    stripped = _plain_copy(device)
    for key in (
        CONF_HOST,
        CONF_LOCAL_KEY,
        CONF_PRODUCT_KEY,
        CONF_PRODUCT_NAME,
    ):
        stripped.pop(key, None)
    return stripped


def _apply_runtime_device_config(hass, config_entry):
    """Apply live-device config changes that do not require entity reload."""
    runtime_devices = hass.data.get(DOMAIN, {}).get(TUYA_DEVICES, {})
    for device_id, dev_config in config_entry.data.get(CONF_DEVICES, {}).items():
        runtime_device = runtime_devices.get(device_id)
        if not runtime_device:
            continue
        changed = runtime_device.update_config(dev_config)
        if changed and not runtime_device.connected:
            runtime_device.async_connect(force=True)


def _copy_config_data(data):
    """Copy config-entry data into mutable plain containers."""
    return _plain_copy(data)


def _plain_copy(value):
    """Copy Home Assistant config data without relying on deepcopy internals."""
    if isinstance(value, Mapping):
        return {key: _plain_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain_copy(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_plain_copy(item) for item in value)
    return value


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    dev_id = list(device_entry.identifiers)[0][1].split("_")[-1]

    ent_reg = er.async_get(hass)
    entities = {
        ent.unique_id: ent.entity_id
        for ent in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
        if dev_id in ent.unique_id
    }
    for entity_id in entities.values():
        ent_reg.async_remove(entity_id)

    if dev_id not in config_entry.data[CONF_DEVICES]:
        _LOGGER.info(
            "Device %s not found in config entry: finalizing device removal", dev_id
        )
        return True

    await hass.data[DOMAIN][TUYA_DEVICES][dev_id].close()

    new_data = config_entry.data.copy()
    new_data[CONF_DEVICES].pop(dev_id)
    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

    hass.config_entries.async_update_entry(
        config_entry,
        data=new_data,
    )

    _LOGGER.info("Device %s removed.", dev_id)

    return True


async def async_remove_orphan_entities(hass, entry):
    """Remove entities associated with config entry that has been removed."""
    ent_reg = er.async_get(hass)
    configured_unique_ids = {
        f"local_{dev_id}_{entity[CONF_ID]}"
        for dev_id, device in entry.data[CONF_DEVICES].items()
        for entity in device[CONF_ENTITIES]
    }
    registered_entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)

    for entity in registered_entities:
        if entity.unique_id in configured_unique_ids:
            continue
        _LOGGER.info("Removing orphaned LocalTuya entity %s", entity.entity_id)
        ent_reg.async_remove(entity.entity_id)
