"""Platform to present any Tuya DP as a number."""
import logging
from functools import partial
import typing

import voluptuous as vol
from homeassistant.components.number import DOMAIN, NumberEntity
from homeassistant.const import CONF_DEVICE_CLASS, STATE_UNKNOWN

from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)

CONF_MIN_VALUE = "min_value"
CONF_MAX_VALUE = "max_value"
CONF_STEP_VALUE = "step_value"
CONF_DP_DTYPE = "dp_data_type"  # it could be float int str

DEFAULT_MIN = 0
DEFAULT_MAX = 100000
DEFAULT_STEP = 1
DEFAULT_DP_DTYPE = "float"

DTYPE_MAPPER = {
    "str": str,
    "float": float,
    "int": int,
}

POSSIBLE_DP_DTYPE: list[typing.Literal["str", "int", "float"]] = list(
    DTYPE_MAPPER.keys()
)


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
        vol.Optional(CONF_STEP_VALUE, default=DEFAULT_STEP): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
        vol.Optional(CONF_DP_DTYPE, default=DEFAULT_DP_DTYPE): vol.In(
            POSSIBLE_DP_DTYPE
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

        if (step_value := self._config.get(CONF_STEP_VALUE, None)) is not None:
            self._attr_step = step_value

        self._max_value = self._config.get(CONF_MAX_VALUE)

        self.dp_dtype_class: typing.Union[
            type[str], type[float], type[int]
        ] = DTYPE_MAPPER[self._config.get(CONF_DP_DTYPE)]

    @property
    def value(self) -> float:
        """Return sensor state."""
        return self._state

    @property
    def min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_set_value(self, value: float) -> None:
        """Update the current value."""
        casted_value = self.dp_dtype_class(value)
        await self._device.set_dp(casted_value, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        state = self.dps(self._dp_id)
        self._state = state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaNumber, flow_schema)
