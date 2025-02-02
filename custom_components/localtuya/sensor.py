"""Platform to present any Tuya DP as a sensor."""
import logging
from functools import partial
from .config_flow import _col_to_select

import voluptuous as vol
from homeassistant.components.sensor import DEVICE_CLASSES, DOMAIN, SensorEntity, SensorStateClass
from homeassistant.components.sensor import (
    DEVICE_CLASSES_SCHEMA,
    DOMAIN,
    STATE_CLASSES_SCHEMA,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_SCALING, CONF_STATE_CLASS

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 2


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_STATE_CLASS): _col_to_select(
            [sc.value for sc in SensorStateClass]
        ),
        vol.Optional(CONF_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
    }


class LocaltuyaSensor(LocalTuyaEntity, SensorEntity):
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
    def state_class(self):
        """Return longterm statistics."""
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    @property
    def state_class(self) -> str | None:
        """Return state class."""
        return self._config.get(CONF_STATE_CLASS)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    def status_updated(self):
        """Device status was updated."""
        state = self.dp_value(self._dp_id)

        self._state = self.scale(state)

    # No need to restore state for a sensor
    async def restore_state_when_connected(self):
        """Do nothing for a sensor."""
        return


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSensor, flow_schema)
