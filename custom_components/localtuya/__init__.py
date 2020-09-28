"""The LocalTuya integration integration.

Sample YAML config with all supported entity types (default values
are pre-filled for optional fields):

localtuya:
  - host: 192.168.1.x
    device_id: xxxxx
    local_key: xxxxx
    friendly_name: Tuya Device
    protocol_version: "3.3"
    entities:
      - platform: binary_sensor
        friendly_name: Plug Status
        id: 1
        device_class: power
        state_on: "true" # Optional
        state_off: "false" # Optional

      - platform: cover
        friendly_name: Device Cover
        id: 2
        open_close_cmds: ["on_off","open_close"] # Optional, default: "on_off"
        positioning_mode: ["none","position","fake"] # Optional, default: "none"
        currpos_dp: 3 # Optional, required only for "position" mode
        setpos_dp: 4  # Optional, required only for "position" mode
        span_time: 25 # Full movement time: Optional, required only for "fake" mode

      - platform: fan
        friendly_name: Device Fan
        id: 3

      - platform: light
        friendly_name: Device Light
        id: 4

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
"""
import asyncio
import logging
from datetime import timedelta, datetime

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_PLATFORM,
    CONF_ENTITIES,
    SERVICE_RELOAD,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.reload import async_integration_yaml_config

from .const import DOMAIN, TUYA_DEVICE
from .config_flow import config_schema
from .common import TuyaDevice

_LOGGER = logging.getLogger(__name__)

UNSUB_LISTENER = "unsub_listener"
UNSUB_TRACK = "unsub_track"

POLL_INTERVAL = 30

CONFIG_SCHEMA = config_schema()


@callback
def _async_update_config_entry_if_from_yaml(hass, entries_by_id, conf):
    """Update a config entry with the latest yaml."""
    device_id = conf[CONF_DEVICE_ID]

    if device_id in entries_by_id and entries_by_id[device_id].source == SOURCE_IMPORT:
        entry = entries_by_id[device_id]
        hass.config_entries.async_update_entry(entry, data=conf.copy())


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    hass.data.setdefault(DOMAIN, {})

    async def _handle_reload(service):
        """Handle reload service call."""
        config = await async_integration_yaml_config(hass, DOMAIN)

        if not config or DOMAIN not in config:
            return

        current_entries = hass.config_entries.async_entries(DOMAIN)
        entries_by_id = {entry.data[CONF_DEVICE_ID]: entry for entry in current_entries}

        for conf in config[DOMAIN]:
            _async_update_config_entry_if_from_yaml(hass, entries_by_id, conf)

        reload_tasks = [
            hass.config_entries.async_reload(entry.entry_id)
            for entry in current_entries
        ]

        await asyncio.gather(*reload_tasks)

    hass.helpers.service.async_register_admin_service(
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    for host_config in config.get(DOMAIN, []):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=host_config
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    unsub_listener = entry.add_update_listener(update_listener)

    device = TuyaDevice(hass, entry.data)

    async def update_state(now):
        """Read device status and update platforms."""
        status = None
        try:
            status = await hass.async_add_executor_job(device.status)
        except Exception:
            _LOGGER.debug("update failed")

        signal = f"localtuya_{entry.data[CONF_DEVICE_ID]}"
        async_dispatcher_send(hass, signal, status)

    unsub_track = async_track_time_interval(
        hass, update_state, timedelta(seconds=POLL_INTERVAL)
    )

    hass.data[DOMAIN][entry.entry_id] = {
        UNSUB_LISTENER: unsub_listener,
        UNSUB_TRACK: unsub_track,
        TUYA_DEVICE: device,
    }

    async def setup_entities():
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_setup(
                    entry, entity[CONF_PLATFORM]
                )
                for entity in entry.data[CONF_ENTITIES]
            ]
        )

        await update_state(datetime.now())

    hass.async_create_task(setup_entities())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in set(
                    entity[CONF_PLATFORM] for entity in entry.data[CONF_ENTITIES]
                )
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id][UNSUB_LISTENER]()
    hass.data[DOMAIN][entry.entry_id][UNSUB_TRACK]()
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)
