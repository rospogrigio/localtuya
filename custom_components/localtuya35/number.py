"""Platform to present any Tuya DP as a number."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.number import DOMAIN, NumberEntity
from homeassistant.const import CONF_DEVICE_CLASS, STATE_UNKNOWN

from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)

CONF_MIN_VALUE = "native_min_value"
CONF_MAX_VALUE = "native_max_value"

DEFAULT_MIN = 0
DEFAULT_MAX = 100000


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_MIN_VALUE, default=DEFAULT_MIN): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
        vol.Required(CONF_MAX_VALUE, default=DEFAULT_MAX): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
    }


class LocaltuyaNumber(LocalTuyaEntity, NumberEntity):
    """Representation of a Tuya Number."""

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

        self._min_value = DEFAULT_MIN
        if CONF_MIN_VALUE in self._config:
            self._min_value = self._config.get(CONF_MIN_VALUE)

        self._max_value = self._config.get(CONF_MAX_VALUE)

    @property
    def native_value(self) -> float:
        """Return sensor state."""
        return self._state

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._device.set_dp(value, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        state = self.dps(self._dp_id)
        self._state = state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaNumber, flow_schema)
