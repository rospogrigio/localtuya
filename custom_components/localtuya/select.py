"""Platform to present any Tuya DP as an enumeration."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.select import DOMAIN, SelectEntity
from homeassistant.const import CONF_DEVICE_CLASS, STATE_UNKNOWN

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_DEFAULT_VALUE,
    CONF_OPTIONS,
    CONF_OPTIONS_FRIENDLY,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_OPTIONS): str,
        vol.Optional(CONF_OPTIONS_FRIENDLY): str,
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
        vol.Required(CONF_PASSIVE_ENTITY): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
    }


_LOGGER = logging.getLogger(__name__)


class LocaltuyaSelect(LocalTuyaEntity, SelectEntity):
    """Representation of a Tuya Enumeration."""

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
        self._state_friendly = ""
        self._valid_options = self._config.get(CONF_OPTIONS).split(";")

        # Set Display options
        self._display_options = []
        display_options_str = ""
        if CONF_OPTIONS_FRIENDLY in self._config:
            display_options_str = self._config.get(CONF_OPTIONS_FRIENDLY).strip()
        _LOGGER.debug("Display Options Configured: %s", display_options_str)

        if display_options_str.find(";") >= 0:
            self._display_options = display_options_str.split(";")
        elif len(display_options_str.strip()) > 0:
            self._display_options.append(display_options_str)
        else:
            # Default display string to raw string
            _LOGGER.debug("No Display options configured - defaulting to raw values")
            self._display_options = self._valid_options

        _LOGGER.debug(
            "Total Raw Options: %s - Total Display Options: %s",
            str(len(self._valid_options)),
            str(len(self._display_options)),
        )
        if len(self._valid_options) > len(self._display_options):
            # If list of display items smaller than list of valid items,
            # then default remaining items to be the raw value
            _LOGGER.debug(
                "Valid options is larger than display options - \
                           filling up with raw values"
            )
            for i in range(len(self._display_options), len(self._valid_options)):
                self._display_options.append(self._valid_options[i])

    @property
    def current_option(self) -> str:
        """Return the current value."""
        return self._state_friendly

    @property
    def options(self) -> list:
        """Return the list of values."""
        return self._display_options

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        option_value = self._valid_options[self._display_options.index(option)]
        _LOGGER.debug("Sending Option: " + option + " -> " + option_value)
        await self._device.set_dp(option_value, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

        state = self.dps(self._dp_id)

        # Check that received status update for this entity.
        if state is not None:
            try:
                self._state_friendly = self._display_options[
                    self._valid_options.index(state)
                ]
            except Exception:  # pylint: disable=broad-except
                # Friendly value couldn't be mapped
                self._state_friendly = state

    # Default value is the first option
    def entity_default_value(self):
        """Return the first option as the default value for this entity type."""
        return self._valid_options[0]


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSelect, flow_schema)
