"""Platform to locally control Tuya-based switch devices."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.number import DOMAIN, NumberEntity
from homeassistant.components.number.const import MODE_BOX, MODE_SLIDER, DEFAULT_MIN_VALUE, DEFAULT_MAX_VALUE, \
    MODE_AUTO, DEFAULT_STEP
from homeassistant.components.sensor import DEVICE_CLASSES
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT, CONF_DEVICE_CLASS

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_MIN_VALUE, CONF_MAX_VALUE, CONF_VALUE_STEP, CONF_CONTROL_MODE, CONF_TUYA_TYPE,
    TUYA_TYPE_FLOAT, TUYA_TYPE_FLOAT_STRING, TUYA_TYPE_INT_STRING, TUYA_TYPE_INT, TUYA_TYPES,
)

CONTROL_MODES = (MODE_AUTO, MODE_BOX, MODE_SLIDER)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_MIN_VALUE, default=DEFAULT_MIN_VALUE): vol.Coerce(float),
        vol.Optional(CONF_MAX_VALUE, default=DEFAULT_MAX_VALUE): vol.Coerce(float),
        vol.Optional(CONF_VALUE_STEP, default=DEFAULT_STEP): vol.Coerce(float),
        vol.Required(CONF_CONTROL_MODE, default=MODE_AUTO): vol.In(CONTROL_MODES),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(DEVICE_CLASSES),
        vol.Required(CONF_TUYA_TYPE, default=TUYA_TYPE_FLOAT): vol.In(TUYA_TYPES)
    }


class LocaltuyaNumber(LocalTuyaEntity, NumberEntity):
    """Representation of a Tuya select."""

    def __init__(
            self,
            device,
            config_entry,
            select_id,
            **kwargs,
    ):
        """Initialize the Tuya switch."""
        super().__init__(device, config_entry, select_id, _LOGGER, **kwargs)
        self._state = None
        print("Initialized number [{}]".format(self.name))

    @property
    def value(self):
        return self._state

    @property
    def min_value(self):
        return self._config.get(CONF_MIN_VALUE, DEFAULT_MIN_VALUE)

    @property
    def max_value(self):
        return self._config.get(CONF_MAX_VALUE, DEFAULT_MAX_VALUE)

    @property
    def step(self):
        return self._config.get(CONF_VALUE_STEP, DEFAULT_STEP)

    @property
    def mode(self):
        return self._config.get(CONF_CONTROL_MODE, MODE_AUTO)

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    async def async_set_value(self, value: float) -> None:
        """Sets value to the device"""
        normalized_value = self.normalize_value(value)
        self.debug("Setting value to the: %f as %s (%s)", value, normalized_value, type(normalized_value))
        await self._device.set_dp(normalized_value, self._dp_id)

    def normalize_value(self, value: float):
        """Converts value to the proper Tuya type"""
        tuya_type = self._config.get(CONF_TUYA_TYPE, TUYA_TYPE_FLOAT)
        if tuya_type == TUYA_TYPE_FLOAT_STRING:
            return str(value)
        elif tuya_type == TUYA_TYPE_INT_STRING:
            return str(int(value))
        elif tuya_type == TUYA_TYPE_INT:
            return int(value)
        else:
            return value

    def status_updated(self):
        """Device status was updated."""
        raw_value = self.dps(self._dp_id)
        self.debug("Setting value from: %s (%s)", raw_value, type(raw_value))
        try:
            self._state = float(raw_value)
        except ValueError:
            self.warning("Incorrect value received: %s", raw_value)
            pass
        except TypeError:
            self.warning("Incorrect value received: %s, %s", raw_value, type(raw_value))
            pass
        except OverflowError:
            self.warning("Received out of bounds value: %s", raw_value)
            pass


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaNumber, flow_schema)
