"""Platform to present any Tuya DP as a sensor."""
import logging
import base64
import re
from functools import partial

import voluptuous as vol
from homeassistant.components.sensor import DEVICE_CLASSES, DOMAIN
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_SCALING, CONF_BASE64_DECODE, CONF_BYTES_RANGE, CONF_ROUND_PRECISION

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 2


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(DEVICE_CLASSES),
        vol.Optional(CONF_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        vol.Optional(CONF_BASE64_DECODE): vol.Coerce(bool),
        vol.Optional(CONF_BYTES_RANGE): str,
        vol.Optional(CONF_ROUND_PRECISION): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=3)
        ),
    }

class LocaltuyaSensor(LocalTuyaEntity):
    """Representation of a Tuya sensor."""

    def __init__(
        self,
        device,
        config_entry,
        config_entity,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        super().__init__(device, config_entry, config_entity, _LOGGER, **kwargs)
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
        if state is None: 
           self._state = state
        else:
          scale_factor = self._config.get(CONF_SCALING)
          base64_dec = self._config.get(CONF_BASE64_DECODE)
          bin_byte_range = self._config.get(CONF_BYTES_RANGE)
          round_precision = self._config.get(CONF_ROUND_PRECISION)
          if base64_dec is not None and base64_dec == True:
              state = base64.b64decode(state)
          if bin_byte_range is not None:
              ranges = bin_byte_range.split(":")
              state = state[int(ranges[0]):(int(ranges[0])+int(ranges[1]))]
              state = int.from_bytes(state, byteorder='big')
          if scale_factor is not None and isinstance(state, (int, float)):
              state = state * scale_factor;
          if round_precision is not None and isinstance(state, (float)):
              round_precision = int(round_precision)
              state = round(state,round_precision)
              if round_precision == 0: state = int(state)
          self._state = state

    # No need to restore state for a sensor
    async def restore_state_when_connected(self):
        """Do nothing for a sensor."""
        return


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSensor, flow_schema)
