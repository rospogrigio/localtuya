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

import voluptuous as vol

from homeassistant.components.switch import (
    SwitchEntity,
    DOMAIN,
)
from homeassistant.const import CONF_ID

from .const import (
    ATTR_CURRENT,
    ATTR_CURRENT_CONSUMPTION,
    ATTR_VOLTAGE,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_VOLTAGE,
)
from .common import LocalTuyaEntity, prepare_setup_entities

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT): vol.In(dps),
        vol.Optional(CONF_CURRENT_CONSUMPTION): vol.In(dps),
        vol.Optional(CONF_VOLTAGE): vol.In(dps),
    }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up a Tuya switch based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(
        hass, config_entry, DOMAIN
    )
    if not entities_to_setup:
        return

    switches = []
    for device_config in entities_to_setup:
        switches.append(
            LocaltuyaSwitch(
                tuyainterface,
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(switches, True)


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
            "Initialized switch [{}] with status [{}] and state [{}]".format(
                self.name, self._status, self._state
            )
        )

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return device state attributes."""
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
