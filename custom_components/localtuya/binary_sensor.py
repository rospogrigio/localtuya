"""Platform to present any Tuya DP as a binary sensor."""

import logging
import voluptuous as vol

from functools import partial

from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig
from homeassistant.helpers.event import async_call_later
from homeassistant.core import callback, CALLBACK_TYPE
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    DOMAIN,
    BinarySensorEntity,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_STATE_ON, CONF_RESET_TIMER


CONF_STATE_OFF = "state_off"

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_STATE_ON, default="True"): str,
        # vol.Required(CONF_STATE_OFF, default="False"): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_RESET_TIMER, default=0): NumberSelector(
            NumberSelectorConfig(min=0, unit_of_measurement="Seconds", mode="box")
        ),
    }


class LocalTuyaBinarySensor(LocalTuyaEntity, BinarySensorEntity):
    """Representation of a Tuya binary sensor."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya binary sensor."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._is_on = False

        self._reset_timer: float = self._config.get(CONF_RESET_TIMER, 0)
        self._reset_timer_interval: CALLBACK_TYPE | None = None

    @property
    def is_on(self):
        """Return sensor state."""
        return self._is_on

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

        state = str(self.dp_value(self._dp_id)).lower()
        # users may set wrong on states, But we assume that must devices use this on states.
        possible_on_states = ["true", "1", "pir", "on"]
        if state == self._config[CONF_STATE_ON].lower() or state in possible_on_states:
            self._is_on = True
        else:
            self._is_on = False

        if self._reset_timer and self._is_on:
            if self._reset_timer_interval is not None:
                self._reset_timer_interval()
                self._reset_timer_interval = None

            @callback
            def async_reset_state(now):
                """Set the state of the entity to off."""
                # "_update_handler" logic, if status hasn't changed "status_updated" will not be called.
                # Maybe we can find better solution then this workaround?
                self._status[self._dp_id] = "reset_state_binary_sensor"
                self._is_on = False
                self.async_write_ha_state()

            self._reset_timer_interval = async_call_later(
                self.hass, self._reset_timer, async_reset_state
            )

    # No need to restore state for a sensor
    async def restore_state_when_connected(self):
        """Do nothing for a sensor."""
        return


async_setup_entry = partial(
    async_setup_entry, DOMAIN, LocalTuyaBinarySensor, flow_schema
)
