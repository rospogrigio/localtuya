"""Platform to locally control Tuya-based vacuum devices."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.vacuum import (
    DOMAIN,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_IDLE,
    STATE_RETURNING,
    SUPPORT_BATTERY,
    SUPPORT_FAN_SPEED,
    SUPPORT_PAUSE,
    SUPPORT_RETURN_HOME,
    SUPPORT_START,
    SUPPORT_STATE,
    SUPPORT_STATUS,
    SUPPORT_STOP,
    StateVacuumEntity,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_BATTERY_DP,
    CONF_CLEANING_MODE_DP,
    CONF_CLEANING_MODES,
    CONF_COMMANDS_DP,
    CONF_COMMANDS_SET,
    CONF_DOCKED_STATUS_VALUE,
    CONF_FAN_SPEED_DP,
    CONF_FAN_SPEEDS,
    CONF_IDLE_STATUS_VALUE,
    CONF_RETURNING_STATUS_VALUE,
)

_LOGGER = logging.getLogger(__name__)

CURRENT_CLEANING_MODE = "Current cleaning mode"
CURRENT_FAN_SPEED = "Current fan speed"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_COMMANDS_SET): str,
        vol.Required(CONF_COMMANDS_DP): vol.In(dps),
        vol.Required(CONF_IDLE_STATUS_VALUE): str,
        vol.Required(CONF_DOCKED_STATUS_VALUE): str,
        vol.Optional(CONF_RETURNING_STATUS_VALUE): str,
        vol.Optional(CONF_BATTERY_DP): vol.In(dps),
        vol.Optional(CONF_CLEANING_MODE_DP): vol.In(dps),
        vol.Optional(CONF_CLEANING_MODES, default=""): str,
        vol.Optional(CONF_FAN_SPEED_DP): vol.In(dps),
        vol.Optional(CONF_FAN_SPEEDS, default=""): str,
    }


class LocaltuyaVacuum(LocalTuyaEntity, StateVacuumEntity):
    """Tuya vacuum device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaVacuum."""
        super().__init__(device, config_entry, switchid, **kwargs)
        self._state = None
        self._commands_set = self._config[CONF_COMMANDS_SET].split(",")
        self._battery_level = None

        self._cleaning_modes_list = []
        if self.has_config(CONF_CLEANING_MODES):
            self._cleaning_modes_list = self._config[CONF_CLEANING_MODES].split(",")

        self._fan_speed_list = []
        if self.has_config(CONF_FAN_SPEEDS):
            self._fan_speed_list = self._fan_speed_list + self._config[
                CONF_FAN_SPEEDS
            ].split(",")

        self._fan_speed = ""

        self._attrs = {}

        print(
            "Initialized vacuum [{}] with fan speeds [{}]".format(
                self.name, self._fan_speed_list
            )
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        features = (
            SUPPORT_RETURN_HOME
            | SUPPORT_PAUSE
            | SUPPORT_STOP
            | SUPPORT_STATUS
            | SUPPORT_STATE
            | SUPPORT_START
        )
        if self.has_config(CONF_RETURNING_STATUS_VALUE):
            features = features | SUPPORT_RETURN_HOME
        if self.has_config(CONF_CLEANING_MODE_DP) or self.has_config(CONF_FAN_SPEED_DP):
            features = features | SUPPORT_FAN_SPEED
        if self.has_config(CONF_BATTERY_DP):
            features = features | SUPPORT_BATTERY

        return features

    @property
    def state(self):
        """Return the vacuum state."""
        return self._state

    @property
    def battery_level(self):
        """Return the current battery level."""
        return self._battery_level

    @property
    def device_state_attributes(self):
        """Return the specific state attributes of this vacuum cleaner."""
        return self._attrs

    @property
    def fan_speed(self):
        """Return the current cleaning mode."""
        return self._fan_speed

    @property
    def fan_speed_list(self) -> list:
        """Return the list of available fan speeds and cleaning modes."""
        return self._cleaning_modes_list + self._fan_speed_list

    @property
    def error(self):
        """Return error message."""
        return ""

    async def async_start(self, **kwargs):
        """Turn the vacuum on and start cleaning."""
        await self._device.set_dp(self._commands_set[0], self._config[CONF_COMMANDS_DP])

    async def async_pause(self, **kwargs):
        """Stop the vacuum cleaner, do not return to base."""
        if len(self._commands_set) > 1:
            await self._device.set_dp(
                self._commands_set[1], self._config[CONF_COMMANDS_DP]
            )
        else:
            _LOGGER.error("Missing command for pause in commands set.")

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        if len(self._commands_set) > 2:
            await self._device.set_dp(
                self._commands_set[2], self._config[CONF_COMMANDS_DP]
            )
        else:
            _LOGGER.error("Missing command for pause in commands set.")

    async def async_stop(self, **kwargs):
        """Turn the vacuum off stopping the cleaning and returning home."""
        if len(self._commands_set) > 2:
            await self._device.set_dp(
                self._commands_set[2], self._config[CONF_COMMANDS_DP]
            )
        else:
            _LOGGER.error("Missing command for pause in commands set.")

    async def async_clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        return None

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        return None

    async def async_set_fan_speed(self, **kwargs):
        """Set the cleaning mode."""
        fan_speed = kwargs["fan_speed"]
        if fan_speed in self._cleaning_modes_list:
            print("SET NEW CM [{}]".format(fan_speed))
            await self._device.set_dp(fan_speed, self._config[CONF_CLEANING_MODE_DP])
        if fan_speed in self._fan_speed_list:
            print("SET NEW FL [{}]".format(fan_speed))
            await self._device.set_dp(fan_speed, self._config[CONF_FAN_SPEED_DP])

    def status_updated(self):
        """Device status was updated."""
        state_value = str(self.dps(self._dp_id))
        if state_value == self._config[CONF_IDLE_STATUS_VALUE]:
            self._state = STATE_IDLE
        elif state_value == self._config[CONF_DOCKED_STATUS_VALUE]:
            self._state = STATE_DOCKED
        elif state_value == self._config.get(CONF_RETURNING_STATUS_VALUE, ""):
            self._state = STATE_RETURNING
        else:
            self._state = STATE_CLEANING

        if self.has_config(CONF_BATTERY_DP):
            # testing
            # self._battery_level = round(self.dps_conf(CONF_BATTERY_DP) / 2300 * 100)
            self._battery_level = self.dps_conf(CONF_BATTERY_DP)

        self._fan_speed = ""
        if self.has_config(CONF_CLEANING_MODES):
            self._attrs[CURRENT_CLEANING_MODE] = self._cleaning_modes_list[0]
            self._fan_speed = self._cleaning_modes_list[0]

        if self.has_config(CONF_FAN_SPEEDS):
            if self._fan_speed != "":
                self._fan_speed = self._fan_speed + "_"

            self._attrs[CURRENT_FAN_SPEED] = self._fan_speed_list[0]
            self._fan_speed = self._fan_speed + self._fan_speed_list[0]


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaVacuum, flow_schema)
