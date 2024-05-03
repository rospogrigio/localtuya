"""Platform to locally control Tuya-based vacuum devices."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.vacuum import (
    DOMAIN,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    StateVacuumEntity, VacuumEntityFeature,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_BATTERY_DP,
    CONF_CLEAN_AREA_DP,
    CONF_CLEAN_RECORD_DP,
    CONF_CLEAN_TIME_DP,
    CONF_DOCKED_STATUS_VALUE,
    CONF_FAN_SPEED_DP,
    CONF_FAN_SPEEDS,
    CONF_FAULT_DP,
    CONF_IDLE_STATUS_VALUE,
    CONF_LOCATE_DP,
    CONF_MODE_DP,
    CONF_MODES,
    CONF_PAUSED_STATE,
    CONF_POWERGO_DP,
    CONF_RETURN_MODE,
    CONF_RETURNING_STATUS_VALUE,
    CONF_STOP_STATUS,
)

_LOGGER = logging.getLogger(__name__)

CLEAN_TIME = "clean_time"
CLEAN_AREA = "clean_area"
CLEAN_RECORD = "clean_record"
MODES_LIST = "cleaning_mode_list"
MODE = "cleaning_mode"
FAULT = "fault"

DEFAULT_IDLE_STATUS = "standby,sleep"
DEFAULT_RETURNING_STATUS = "docking"
DEFAULT_DOCKED_STATUS = "charging,chargecompleted"
DEFAULT_MODES = "smart,wall_follow,spiral,single"
DEFAULT_FAN_SPEEDS = "low,normal,high"
DEFAULT_PAUSED_STATE = "paused"
DEFAULT_RETURN_MODE = "chargego"
DEFAULT_STOP_STATUS = "standby"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_IDLE_STATUS_VALUE, default=DEFAULT_IDLE_STATUS): str,
        vol.Required(CONF_POWERGO_DP): vol.In(dps),
        vol.Required(CONF_DOCKED_STATUS_VALUE, default=DEFAULT_DOCKED_STATUS): str,
        vol.Optional(
            CONF_RETURNING_STATUS_VALUE, default=DEFAULT_RETURNING_STATUS
        ): str,
        vol.Optional(CONF_BATTERY_DP): vol.In(dps),
        vol.Optional(CONF_MODE_DP): vol.In(dps),
        vol.Optional(CONF_MODES, default=DEFAULT_MODES): str,
        vol.Optional(CONF_RETURN_MODE, default=DEFAULT_RETURN_MODE): str,
        vol.Optional(CONF_FAN_SPEED_DP): vol.In(dps),
        vol.Optional(CONF_FAN_SPEEDS, default=DEFAULT_FAN_SPEEDS): str,
        vol.Optional(CONF_CLEAN_TIME_DP): vol.In(dps),
        vol.Optional(CONF_CLEAN_AREA_DP): vol.In(dps),
        vol.Optional(CONF_CLEAN_RECORD_DP): vol.In(dps),
        vol.Optional(CONF_LOCATE_DP): vol.In(dps),
        vol.Optional(CONF_FAULT_DP): vol.In(dps),
        vol.Optional(CONF_PAUSED_STATE, default=DEFAULT_PAUSED_STATE): str,
        vol.Optional(CONF_STOP_STATUS, default=DEFAULT_STOP_STATUS): str,
    }


class LocaltuyaVacuum(LocalTuyaEntity, StateVacuumEntity):
    """Tuya vacuum device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaVacuum."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._battery_level = None
        self._attrs = {}

        self._idle_status_list = []
        if self.has_config(CONF_IDLE_STATUS_VALUE):
            self._idle_status_list = self._config[CONF_IDLE_STATUS_VALUE].split(",")

        self._modes_list = []
        if self.has_config(CONF_MODES):
            self._modes_list = self._config[CONF_MODES].split(",")
            self._attrs[MODES_LIST] = self._modes_list

        self._docked_status_list = []
        if self.has_config(CONF_DOCKED_STATUS_VALUE):
            self._docked_status_list = self._config[CONF_DOCKED_STATUS_VALUE].split(",")

        self._fan_speed_list = []
        if self.has_config(CONF_FAN_SPEEDS):
            self._fan_speed_list = self._config[CONF_FAN_SPEEDS].split(",")

        self._fan_speed = ""
        self._cleaning_mode = ""
        _LOGGER.debug("Initialized vacuum [%s]", self.name)

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = (
            VacuumEntityFeature.START
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.STATUS
            | VacuumEntityFeature.STATE
        )

        if self.has_config(CONF_RETURN_MODE):
            supported_features = supported_features | VacuumEntityFeature.RETURN_HOME
        if self.has_config(CONF_FAN_SPEED_DP):
            supported_features = supported_features | VacuumEntityFeature.FAN_SPEED
        if self.has_config(CONF_BATTERY_DP):
            supported_features = supported_features | VacuumEntityFeature.BATTERY
        if self.has_config(CONF_LOCATE_DP):
            supported_features = supported_features | VacuumEntityFeature.LOCATE

        return supported_features

    @property
    def state(self):
        """Return the vacuum state."""
        return self._state

    @property
    def battery_level(self):
        """Return the current battery level."""
        return self._battery_level

    @property
    def extra_state_attributes(self):
        """Return the specific state attributes of this vacuum cleaner."""
        return self._attrs

    @property
    def fan_speed(self):
        """Return the current fan speed."""
        return self._fan_speed

    @property
    def fan_speed_list(self) -> list:
        """Return the list of available fan speeds."""
        return self._fan_speed_list

    async def async_start(self, **kwargs):
        """Turn the vacuum on and start cleaning."""
        await self._device.set_dp(True, self._config[CONF_POWERGO_DP])

    async def async_pause(self, **kwargs):
        """Stop the vacuum cleaner, do not return to base."""
        await self._device.set_dp(False, self._config[CONF_POWERGO_DP])

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        if self.has_config(CONF_RETURN_MODE):
            await self._device.set_dp(
                self._config[CONF_RETURN_MODE], self._config[CONF_MODE_DP]
            )
        else:
            _LOGGER.error("Missing command for return home in commands set.")

    async def async_stop(self, **kwargs):
        """Turn the vacuum off stopping the cleaning."""
        if self.has_config(CONF_STOP_STATUS):
            await self._device.set_dp(
                self._config[CONF_STOP_STATUS], self._config[CONF_MODE_DP]
            )
        else:
            _LOGGER.error("Missing command for stop in commands set.")

    async def async_clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        return None

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        if self.has_config(CONF_LOCATE_DP):
            await self._device.set_dp("", self._config[CONF_LOCATE_DP])

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        """Set the fan speed."""
        await self._device.set_dp(fan_speed, self._config[CONF_FAN_SPEED_DP])

    async def async_send_command(self, command, params=None, **kwargs):
        """Send a command to a vacuum cleaner."""
        if command == "set_mode" and "mode" in params:
            mode = params["mode"]
            await self._device.set_dp(mode, self._config[CONF_MODE_DP])

    def status_updated(self):
        """Device status was updated."""
        state_value = str(self.dps(self._dp_id))

        if state_value in self._idle_status_list:
            self._state = STATE_IDLE
        elif state_value in self._docked_status_list:
            self._state = STATE_DOCKED
        elif state_value == self._config[CONF_RETURNING_STATUS_VALUE]:
            self._state = STATE_RETURNING
        elif state_value == self._config[CONF_PAUSED_STATE]:
            self._state = STATE_PAUSED
        else:
            self._state = STATE_CLEANING

        if self.has_config(CONF_BATTERY_DP):
            self._battery_level = self.dps_conf(CONF_BATTERY_DP)

        self._cleaning_mode = ""
        if self.has_config(CONF_MODES):
            self._cleaning_mode = self.dps_conf(CONF_MODE_DP)
            self._attrs[MODE] = self._cleaning_mode

        self._fan_speed = ""
        if self.has_config(CONF_FAN_SPEEDS):
            self._fan_speed = self.dps_conf(CONF_FAN_SPEED_DP)

        if self.has_config(CONF_CLEAN_TIME_DP):
            self._attrs[CLEAN_TIME] = self.dps_conf(CONF_CLEAN_TIME_DP)

        if self.has_config(CONF_CLEAN_AREA_DP):
            self._attrs[CLEAN_AREA] = self.dps_conf(CONF_CLEAN_AREA_DP)

        if self.has_config(CONF_CLEAN_RECORD_DP):
            self._attrs[CLEAN_RECORD] = self.dps_conf(CONF_CLEAN_RECORD_DP)

        if self.has_config(CONF_FAULT_DP):
            self._attrs[FAULT] = self.dps_conf(CONF_FAULT_DP)
            if self._attrs[FAULT] != 0:
                self._state = STATE_ERROR


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaVacuum, flow_schema)
