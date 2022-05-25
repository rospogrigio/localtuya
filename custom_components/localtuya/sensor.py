"""Platform to present any Tuya DP as a sensor."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.sensor import DEVICE_CLASSES, DOMAIN
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_SCALING, CONF_BASE_VALUE

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 2


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(DEVICE_CLASSES),
        vol.Optional(CONF_BASE_VALUE): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        vol.Optional(CONF_SCALING): vol.All(
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
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
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
        self._state = self.scale_if_possible(self.dps(self._dp_id))

    def scale_if_possible(self, state):
        """Scales and adjusts with base original value"""
        state_numeric = None
        if isinstance(state, (int, float)):
            state_numeric = state
        elif isinstance(state, str):
            try:
                state_numeric = int(state)
            except OverflowError:
                pass
            except ValueError:
                try:
                    state_numeric = float(state)
                except OverflowError:
                    pass
                except ValueError:
                    pass

        if state_numeric is None:
            return state

        scale_factor = self._config.get(CONF_SCALING)
        if scale_factor is not None:
            state_numeric *= scale_factor

        base_value = self._config.get(CONF_BASE_VALUE)
        if base_value is not None:
            state_numeric += base_value

        return round(state_numeric, DEFAULT_PRECISION)

async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSensor, flow_schema)
