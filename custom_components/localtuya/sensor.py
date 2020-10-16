"""Platform to present any Tuya DP as a sensor."""
import logging
from functools import partial

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN, DEVICE_CLASSES
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)

from .const import CONF_SCALING
from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCALING = 1.0
DEFAULT_PRECISION = 2


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(DEVICE_CLASSES),
        vol.Optional(CONF_SCALING, default=DEFAULT_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
    }


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
        state = self.dps(self._dp_id)
        scale_factor = self._config.get(CONF_SCALING)
        if scale_factor is not None:
            state = round(state * scale_factor, DEFAULT_PRECISION)
        self._state = state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSensor, flow_schema)
