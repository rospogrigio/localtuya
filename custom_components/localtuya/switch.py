"""
Simple platform to control LOCALLY Tuya switch devices.

Sample config yaml

switch:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    name: tuya_01
    friendly_name: tuya_01
    protocol_version: 3.3
    switches:
      sw01:
        name: main_plug
        friendly_name: Main Plug
        id: 1
        current: 18
        current_consumption: 19
        voltage: 20
      sw02:
        name: usb_plug
        friendly_name: USB Plug
        id: 7
"""
import logging
from time import time, sleep

import voluptuous as vol

from homeassistant.components.switch import (
    SwitchEntity,
    DOMAIN,
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_ID,
    CONF_SWITCHES,
    CONF_FRIENDLY_NAME,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv

from . import (
    BASE_PLATFORM_SCHEMA,
    TuyaDevice,
    LocalTuyaEntity,
    prepare_setup_entities,
    import_from_yaml,
)
from .const import (
    ATTR_CURRENT,
    ATTR_CURRENT_CONSUMPTION,
    ATTR_VOLTAGE,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_VOLTAGE,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_ID = "1"

# TODO: This will eventully merge with flow_schema
SWITCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
        vol.Optional(CONF_NAME): cv.string,  # Deprecated: not used
        vol.Required(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_CURRENT, default="-1"): cv.string,
        vol.Optional(CONF_CURRENT_CONSUMPTION, default="-1"): cv.string,
        vol.Optional(CONF_VOLTAGE, default="-1"): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA).extend(
    {
        vol.Optional(CONF_CURRENT, default="-1"): cv.string,
        vol.Optional(CONF_CURRENT_CONSUMPTION, default="-1"): cv.string,
        vol.Optional(CONF_VOLTAGE, default="-1"): cv.string,
        vol.Optional(CONF_SWITCHES, default={}): vol.Schema({cv.slug: SWITCH_SCHEMA}),
    }
)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT): vol.In(dps),
        vol.Optional(CONF_CURRENT_CONSUMPTION): vol.In(dps),
        vol.Optional(CONF_VOLTAGE): vol.In(dps),
    }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya switch based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(config_entry, DOMAIN)
    if not entities_to_setup:
        return

    switches = []
    for device_config in entities_to_setup:
        if device_config.get(CONF_CURRENT, "-1") != "-1":
            tuyainterface.add_dps_to_request(device_config.get(CONF_CURRENT))
        if device_config.get(CONF_CURRENT_CONSUMPTION, "-1") != "-1":
            tuyainterface.add_dps_to_request(device_config.get(CONF_CURRENT_CONSUMPTION))
        if device_config.get(CONF_VOLTAGE, "-1") != "-1":
            tuyainterface.add_dps_to_request(device_config.get(CONF_VOLTAGE))

        switches.append(
            LocaltuyaSwitch(
                TuyaDevice(tuyainterface, config_entry.data[CONF_FRIENDLY_NAME]),
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(switches, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    return import_from_yaml(hass, config, DOMAIN)




class LocaltuyaSwitch(LocalTuyaEntity, SwitchEntity):
    """Representation of a Tuya switch."""

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize the Tuya switch."""
        super().__init__(device, config_entry, switchid, **kwargs)
        self._state = None
        print(
            "Initialized tuya switch [{}] with switch status [{}] and state [{}]".format(
                self.name, self._status, self._state
            )
        )

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def device_state_attributes(self):
        attrs = {}
        if self._config.get(CONF_CURRENT, "-1") != "-1":
            attrs[ATTR_CURRENT] = self.dps(self._config[CONF_CURRENT])
        if self._config.get(ATTR_CURRENT_CONSUMPTION, "-1") != "-1":
            attrs[ATTR_CURRENT_CONSUMPTION] = (
                self.dps(self._config[CONF_CURRENT_CONSUMPTION]) / 10
            )
        if self._config.get(CONF_VOLTAGE, "-1") != "-1":
            attrs[ATTR_VOLTAGE] = self.dps(self._config[CONF_VOLTAGE]) / 10
        return attrs

    def turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        self._device.set_dps(True, self._dps_id)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        self._device.set_dps(False, self._dps_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dps_id)
