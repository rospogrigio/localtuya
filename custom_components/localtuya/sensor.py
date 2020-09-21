"""
Platform to prsent any Tuya DP as a sensor.

Sample config yaml

sensor:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    friendly_name: Current
    protocol_version: 3.3
    id: 18
    unit_of_measurement: mA
    device_class: current
"""
import logging
from time import time, sleep

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN, PLATFORM_SCHEMA, DEVICE_CLASSES
from homeassistant.const import (
    CONF_ID,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)

from . import (
    BASE_PLATFORM_SCHEMA,
    TuyaDevice,
    LocalTuyaEntity,
    prepare_setup_entities,
    import_from_yaml,
)
from .const import CONF_SCALING

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCALING = 1.0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(DEVICE_CLASSES),
        vol.Optional(CONF_SCALING, default=DEFAULT_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
    }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya sensor based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(config_entry, DOMAIN)
    if not entities_to_setup:
        return

    sensors = []
    for device_config in entities_to_setup:
        sensors.append(
            LocaltuyaSensor(
                TuyaCache(tuyainterface, config_entry.data[CONF_FRIENDLY_NAME]),
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(sensors, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya sensor."""
    return import_from_yaml(hass, config, DOMAIN)



class LocaltuyaSensor(LocalTuyaEntity):
    """Representation of a Tuya sensor."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        super().__init__(device, config_entry, sensorid, **kwargs)
        self._state = STATE_UNKNOWN

    @property
    def state(self):
        """Return sensor state."""
        scale_factor = self._config.get(CONF_SCALING)
        if scale_factor is not None:
            return self._state * scale_factor
        return self._state

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dps_id)
