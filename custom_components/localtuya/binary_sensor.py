"""
Platform to prsent any Tuya DP as a binary sensor.

Sample config yaml

sensor:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    friendly_name: Current
    protocol_version: 3.3
    id: 18
    state_on: "true" (optional, default is "true")
    state_off: "false" (optional, default is "false")
    device_class: current
"""
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DOMAIN,
    DEVICE_CLASSES_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import CONF_ID, CONF_DEVICE_CLASS

from .common import LocalTuyaEntity, prepare_setup_entities

_LOGGER = logging.getLogger(__name__)

CONF_STATE_ON = "state_on"
CONF_STATE_OFF = "state_off"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_STATE_ON, default="True"): str,
        vol.Required(CONF_STATE_OFF, default="False"): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up a Tuya sensor based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(
        hass, config_entry, DOMAIN
    )
    if not entities_to_setup:
        return

    sensors = []
    for device_config in entities_to_setup:
        sensors.append(
            LocaltuyaBinarySensor(
                tuyainterface,
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(sensors, True)


class LocaltuyaBinarySensor(LocalTuyaEntity, BinarySensorEntity):
    """Representation of a Tuya binary sensor."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya binary sensor."""
        super().__init__(device, config_entry, sensorid, **kwargs)
        self._is_on = False

    @property
    def is_on(self):
        """Return sensor state."""
        return self._is_on

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    def status_updated(self):
        """Device status was updated."""
        state = str(self.dps(self._dps_id)).lower()
        if state == self._config[CONF_STATE_ON].lower():
            self._is_on = True
        elif state == self._config[CONF_STATE_OFF].lower():
            self._is_on = False
        else:
            _LOGGER.warning(
                "State for entity %s did not match state patterns", self.entity_id
            )
