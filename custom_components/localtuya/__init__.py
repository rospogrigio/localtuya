<<<<<<< HEAD
"""The LocalTuya integration integration.

Sample YAML config with all supported entity types (default values
are pre-filled for optional fields):

localtuya:
  - host: 192.168.1.x
    device_id: xxxxx
    local_key: xxxxx # Optional
    friendly_name: Tuya Device
    protocol_version: "3.3"
    is_gateway: false # Optional
    parent_gateway: xxxxx # Optional
    entities: # Optional
      - platform: binary_sensor
        friendly_name: Plug Status
        id: 1
        device_class: power
        state_on: "true" # Optional
        state_off: "false" # Optional

      - platform: cover
        friendly_name: Device Cover
        id: 2
        commands_set: # Optional, default: "on_off_stop"
            ["on_off_stop","open_close_stop","fz_zz_stop","1_2_3"]
        positioning_mode: ["none","position","timed"] # Optional, default: "none"
        currpos_dp: 3 # Optional, required only for "position" mode
        setpos_dp: 4  # Optional, required only for "position" mode
        position_inverted: [True,False] # Optional, default: False
        span_time: 25 # Full movement time: Optional, required only for "timed" mode

      - platform: fan
        friendly_name: Device Fan
        id: 3

      - platform: light
        friendly_name: Device Light
        id: 4
        brightness: 20
        brightness_lower: 29 # Optional
        brightness_upper: 1000 # Optional
        color_temp: 21

      - platform: sensor
        friendly_name: Plug Voltage
        id: 20
        scaling: 0.1 # Optional
        device_class: voltage # Optional
        unit_of_measurement: "V" # Optional

      - platform: switch
        friendly_name: Plug
        id: 1
        current: 18 # Optional
        current_consumption: 19 # Optional
        voltage: 20 # Optional

      - platform: vacuum
        friendly_name: Vacuum
        id: 28
        idle_status_value: "standby,sleep"
        returning_status_value: "docking"
        docked_status_value: "charging,chargecompleted"
        battery_dp: 14
        mode_dp: 27
        modes: "smart,standby,chargego,wall_follow,spiral,single"
        fan_speed_dp: 30
        fan_speeds: "low,normal,high"
        clean_time_dp: 33
        clean_area_dp: 32
"""
=======
"""The LocalTuya integration."""
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b
import asyncio
import logging
import time
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

<<<<<<< HEAD
from .common import (
    TuyaDevice,
    TuyaGatewayDevice,
    TuyaSubDevice,
    async_config_entry_by_device_id,
)
from .config_flow import config_schema
from .const import (
    CONF_PRODUCT_KEY,
    CONF_IS_GATEWAY,
    CONF_PARENT_GATEWAY,
    DATA_DISCOVERY,
    DOMAIN,
    TUYA_DEVICE,
=======
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
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b
)
from .discovery import TuyaDiscovery

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"

RECONNECT_INTERVAL = timedelta(seconds=60)

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

        await asyncio.gather(*reload_tasks)

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
        product_key = device["productKey"]

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

        new_data = entry.data.copy()
        updated = False

        if device_cache[device_id] != device_ip:
            updated = True
            new_data[CONF_DEVICES][device_id][CONF_HOST] = device_ip
            device_cache[device_id] = device_ip

        if dev_entry.get(CONF_PRODUCT_KEY) != product_key:
            updated = True
            new_data[CONF_DEVICES][device_id][CONF_PRODUCT_KEY] = product_key

        # Update settings if something changed, otherwise try to connect. Updating
        # settings triggers a reload of the config entry, which tears down the device
        # so no need to connect in that case.
        if updated:
            _LOGGER.debug(
                "Updating keys for device %s: %s %s", device_id, device_ip, product_key
            )
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            hass.config_entries.async_update_entry(entry, data=new_data)
            device = hass.data[DOMAIN][TUYA_DEVICES][device_id]
            if not device.connected:
                device.async_connect()
        elif device_id in hass.data[DOMAIN][TUYA_DEVICES]:
            # _LOGGER.debug("Device %s found with IP %s", device_id, device_ip)

            device = hass.data[DOMAIN][TUYA_DEVICES][device_id]
            if not device.connected:
                device.async_connect()

    def _shutdown(event):
        """Clean up resources when shutting down."""
        discovery.close()

    async def _async_reconnect(now):
        """Try connecting to devices not already connected to."""
        for device_id, device in hass.data[DOMAIN][TUYA_DEVICES].items():
            if not device.connected:
                device.async_connect()

    async_track_time_interval(hass, _async_reconnect, RECONNECT_INTERVAL)

    hass.helpers.service.async_register_admin_service(
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    hass.helpers.service.async_register_admin_service(
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

<<<<<<< HEAD
    if entry.data.get(CONF_IS_GATEWAY):
        device = TuyaGatewayDevice(hass, entry.data)
    elif not entry.data.get(CONF_IS_GATEWAY) and entry.data.get(CONF_PARENT_GATEWAY):
        device = TuyaSubDevice(hass, entry.data)
    else:
        device = TuyaDevice(hass, entry.data)
=======
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
        _LOGGER.info("Cloud API connection succeeded.")
        res = await tuya_api.async_get_devices_list()
    hass.data[DOMAIN][DATA_CLOUD] = tuya_api
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b

    async def setup_entities(device_ids):
        platforms = set()
        for dev_id in device_ids:
            entities = entry.data[CONF_DEVICES][dev_id][CONF_ENTITIES]
            platforms = platforms.union(
                set(entity[CONF_PLATFORM] for entity in entities)
            )
            hass.data[DOMAIN][TUYA_DEVICES][dev_id] = TuyaDevice(hass, entry, dev_id)

<<<<<<< HEAD
    if not entry.data.get(CONF_IS_GATEWAY):

        async def setup_entities():
            platforms = set(
                entity[CONF_PLATFORM] for entity in entry.data[CONF_ENTITIES]
            )
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_setup(entry, platform)
                    for platform in platforms
                ]
            )
            device.async_connect()
=======
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_setup(entry, platform)
                for platform in platforms
            ]
        )

        for dev_id in device_ids:
            hass.data[DOMAIN][TUYA_DEVICES][dev_id].async_connect()

        await async_remove_orphan_entities(hass, entry)

    hass.async_create_task(setup_entities(entry.data[CONF_DEVICES].keys()))

    unsub_listener = entry.add_update_listener(update_listener)
    hass.data[DOMAIN][entry.entry_id] = {UNSUB_LISTENER: unsub_listener}
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b

        await async_remove_orphan_entities(hass, entry)
        hass.async_create_task(setup_entities())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
<<<<<<< HEAD
    if not entry.data.get(CONF_IS_GATEWAY):
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, component)
                    for component in set(
                        entity[CONF_PLATFORM] for entity in entry.data[CONF_ENTITIES]
                    )
                ]
            )
=======
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
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b
        )

<<<<<<< HEAD
        hass.data[DOMAIN][entry.entry_id][UNSUB_LISTENER]()
        await hass.data[DOMAIN][entry.entry_id][TUYA_DEVICE].close()
        if unload_ok:
            hass.data[DOMAIN].pop(entry.entry_id)
=======
    hass.data[DOMAIN][entry.entry_id][UNSUB_LISTENER]()
    for dev_id, device in hass.data[DOMAIN][TUYA_DEVICES].items():
        if device.connected:
            await device.close()

    if unload_ok:
        hass.data[DOMAIN][TUYA_DEVICES] = {}
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b

    return True


async def update_listener(hass, config_entry):
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
