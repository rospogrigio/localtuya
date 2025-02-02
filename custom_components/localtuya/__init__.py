"""The LocalTuya integration."""
import asyncio
import logging
import time
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
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
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.service import async_register_admin_service

from .cloud_api import TuyaCloudApi
from .common import HassLocalTuyaData, TuyaDevice, async_config_entry_by_device_id
from .config_flow import ENTRIES_VERSION, config_schema
from .const import (
    ATTR_UPDATED_AT,
    CONF_GATEWAY_ID,
    CONF_NODE_ID,
    CONF_NO_CLOUD,
    CONF_PRODUCT_KEY,
    CONF_USER_ID,
    DATA_DISCOVERY,
    DOMAIN,
)
from .discovery import TuyaDiscovery

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"

RECONNECT_INTERVAL = timedelta(seconds=60)
RECONNECT_TASK = "localtuya_reconnect_interval"

CONFIG_SCHEMA = config_schema()

CONF_DP = "dp"
CONF_VALUE = "value"

SERVICE_SET_DP = "set_dp"
SERVICE_SET_DP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_DP): int,
        vol.Required(CONF_VALUE): object,
    }
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    hass.data.setdefault(DOMAIN, {})

    current_entries = hass.config_entries.async_entries(DOMAIN)
    device_cache = {}

    async def _handle_reload(service: ServiceCall):
        """Handle reload service call."""
        _LOGGER.info("Service %s.reload called: reloading integration", DOMAIN)

        current_entries = hass.config_entries.async_entries(DOMAIN)

        reload_tasks = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in current_entries
        ]
        await asyncio.gather(*reload_tasks)

    async def _handle_set_dp(event: ServiceCall):
        """Handle set_dp service call."""
        dev_id = event.data[CONF_DEVICE_ID]
        entry: ConfigEntry = async_config_entry_by_device_id(hass, dev_id)
        if not entry or not entry.entry_id:
            raise HomeAssistantError("unknown device id")

        host = entry.data[CONF_DEVICES][dev_id].get(CONF_HOST)
        device: TuyaDevice = hass.data[DOMAIN][entry.entry_id].devices[host]
        if not device.connected:
            raise HomeAssistantError("not connected to device")
        value = event.data[CONF_VALUE]
        if isinstance(value, dict):
            await device.set_dps(value)
        else:
            await device.set_dp(value, event.data[CONF_DP])

    def _device_discovered(device: dict):
        """Update address of device if it has changed."""
        device_ip = device["ip"]
        device_id = device["gwId"]
        product_key = device["productKey"]
        # If device is not in cache, check if a config entry exists
        entry: ConfigEntry = async_config_entry_by_device_id(hass, device_id)
        if entry is None:
            return

        if device_id not in device_cache or device_id not in device_cache.get(
            device_id, {}
        ):
            if entry and device_id in entry.data[CONF_DEVICES]:
                # Save address from config entry in cache to trigger
                # potential update below
                host_ip = entry.data[CONF_DEVICES][device_id][CONF_HOST]
                device_cache[device_id] = {device_id: host_ip}

        for subdev_id, dev_config in entry.data[CONF_DEVICES].items():
            if dev_config.get(CONF_NODE_ID):
                if gateway_id := dev_config.get(CONF_GATEWAY_ID):
                    if entry and device_id == gateway_id:
                        device_cache[device_id] = device_cache.get(device_id, {})
                        device_cache[device_id].update(
                            {subdev_id: dev_config.get(CONF_HOST)}
                        )

        if device_id not in device_cache:
            return
        if not entry.state == ConfigEntryState.LOADED:
            return

        new_data = entry.data.copy()
        updated = False
        for dev_id, host in device_cache[device_id].items():
            if dev_id not in entry.data[CONF_DEVICES]:
                continue
            dev_entry = entry.data[CONF_DEVICES][dev_id]
            if host != device_ip:
                updated = True
                new_data[CONF_DEVICES][dev_id][CONF_HOST] = device_ip
                device_cache[device_id][dev_id] = device_ip

            if (p_key := dev_entry.get(CONF_PRODUCT_KEY)) and p_key != product_key:
                updated = True
                new_data[CONF_DEVICES][dev_id][CONF_PRODUCT_KEY] = product_key
        # Update settings if something changed, otherwise try to connect. Updating
        # settings triggers a reload of the config entry, which tears down the device
        # so no need to connect in that case.
        if updated:
            _LOGGER.debug(
                "Updating keys for device %s: %s %s", device_id, device_ip, product_key
            )
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            hass.config_entries.async_update_entry(entry, data=new_data)

    def _shutdown(event):
        """Clean up resources when shutting down."""
        discovery.close()

    async def _async_reconnect(now):
        """Try connecting to devices not already connected to."""
        for device_id, device in hass.data[DOMAIN][TUYA_DEVICES].items():
            if not device.connected:
                hass.create_task(device.async_connect())

    async_track_time_interval(hass, _async_reconnect, RECONNECT_INTERVAL)

    async_register_admin_service(
        hass,
    )
    hass.services.async_register(DOMAIN, SERVICE_RELOAD, _handle_reload)

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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entries merging all of them in one."""
    new_version = ENTRIES_VERSION
    stored_entries = hass.config_entries.async_entries(DOMAIN)
    if config_entry.version == 1:
        # This an old version of original integration no nned to put it here.
        pass
    if config_entry.version == 2:
        # Switch config flow to selectors convert DP IDs from int to str require HA 2022.4.
        _LOGGER.debug("Migrating config entry from version %s", config_entry.version)
        new_data = config_entry.data.copy()
        for device in new_data[CONF_DEVICES]:
            i = 0
            for _ent in new_data[CONF_DEVICES][device][CONF_ENTITIES]:
                ent_items = {}
                for k, v in _ent.items():
                    ent_items[k] = str(v) if type(v) is int else v
                new_data[CONF_DEVICES][device][CONF_ENTITIES][i].update(ent_items)
                i = i + 1
        config_entry.version = new_version
        hass.config_entries.async_update_entry(config_entry, data=new_data)

    _LOGGER.info(
        "Entry %s successfully migrated to version %s.",
        config_entry.entry_id,
        new_version,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    unsub_listener = entry.add_update_listener(update_listener)
    hass.data[DOMAIN][UNSUB_LISTENER] = unsub_listener
    hass.data[DOMAIN][TUYA_DEVICES] = {}
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
        entry.async_create_background_task(
            hass, tuya_api.async_connect(), "localtuya-cloudAPI"
        )

    async def setup_entities(entry_devices: dict):
        platforms = set()
        devices: dict[str, TuyaDevice] = {}
        for dev_id, config in entry_devices.items():
            host = config.get(CONF_HOST)
            entities = entry.data[CONF_DEVICES][dev_id][CONF_ENTITIES]
            platforms = platforms.union(
                set(entity[CONF_PLATFORM] for entity in entities)
            )

            if node_id := config.get(CONF_NODE_ID):
                # Setup sub device as gateway if there is no gateway exist.
                if host not in devices:
                    devices[host] = TuyaDevice(hass, entry, dev_id, True)

                host = f"{host}_{node_id}"

            devices[host] = TuyaDevice(hass, entry, dev_id)

        hass_localtuya = HassLocalTuyaData(tuya_api, devices, [])
        hass.data[DOMAIN][entry.entry_id] = hass_localtuya

        await async_remove_orphan_entities(hass, entry)
        await hass.config_entries.async_forward_entry_setups(entry, platforms)

        # Connect to tuya devices.
        connect_to_devices = [
            device.async_connect() for device in hass_localtuya.devices.values()
        ]
        # Update listener: add to unsub_listeners
        entry_update = entry.add_update_listener(update_listener)
        hass_localtuya.unsub_listeners.append(entry_update)

        await asyncio.gather(*connect_to_devices)

    await setup_entities(entry.data[CONF_DEVICES])

    # Add reconnect task.
    reconnectTask(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading the Tuya platforms."""
    # Get used platforms.
    platforms = {}
    disconnect_devices = []
    hass_data: HassLocalTuyaData = hass.data[DOMAIN][entry.entry_id]

    for dev in hass_data.devices.values():
        disconnect_devices.append(dev.close())
        for entity in dev._device_config[CONF_ENTITIES]:
            platforms[entity[CONF_PLATFORM]] = True

    # Unload the platforms.
    await hass.config_entries.async_unload_platforms(entry, platforms)

    # Close all connection to the devices.
    # Just to prevent the loop get stuck in-case it calls multiples quickly
    try:
        await asyncio.wait_for(asyncio.gather(*disconnect_devices), 3)
    except:
        pass

    # Unsub events.
    [unsub() for unsub in hass_data.unsub_listeners]

    hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


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

    # host = config_entry.data[CONF_DEVICES][dev_id][CONF_HOST]
    # await hass.data[DOMAIN][config_entry.entry_id].devices[host].close()

    new_data = config_entry.data.copy()
    new_data[CONF_DEVICES].pop(dev_id)
    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

    hass.config_entries.async_update_entry(
        config_entry,
        data=new_data,
    )

    _LOGGER.info("Device %s removed.", dev_id)

    return True


def reconnectTask(hass: HomeAssistant, entry: ConfigEntry):
    """Add a task to reconnect to the devices if is not connected [interval: RECONNECT_INTERVAL]"""
    hass_localtuya: HassLocalTuyaData = hass.data[DOMAIN][entry.entry_id]

    async def _async_reconnect(now):
        """Try connecting to devices not already connected to."""
        for host, dev in hass_localtuya.devices.items():
            if not dev.connected:
                entry.async_create_background_task(
                    hass, dev.async_connect(), f"reconnect_{host}"
                )

    # Add unsub callbeack in unsub_listeners object.
    hass_localtuya.unsub_listeners.append(
        async_track_time_interval(hass, _async_reconnect, RECONNECT_INTERVAL)
    )


async def async_remove_orphan_entities(hass, entry):
    """Remove entities associated with config entry that has been removed."""
    return
    ent_reg = er.async_get(hass)
    entities = {
        ent.unique_id: ent.entity_id
        for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    }
    _LOGGER.info("ENTITIES ORPHAN %s", entities)
    return

    for entity in entry.data[CONF_ENTITIES]:
        if entity[CONF_ID] in entities:
            del entities[entity[CONF_ID]]

    for entity_id in entities.values():
        ent_reg.async_remove(entity_id)
