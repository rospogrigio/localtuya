"""Platform to locally control Tuya-based vacuum devices."""

import logging
from functools import partial
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.vacuum import (
    DOMAIN,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)

from .entity import LocalTuyaEntity, async_setup_entry
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
    CONF_PAUSE_DP,
)

_LOGGER = logging.getLogger(__name__)

CLEAN_TIME = "clean_time"
CLEAN_AREA = "clean_area"
CLEAN_RECORD = "clean_record"
MODES_LIST = "cleaning_mode_list"
MODE = "cleaning_mode"
FAULT = "fault"

DEFAULT_IDLE_STATUS = "standby,sleep"
DEFAULT_RETURNING_STATUS = "docking,to_charge,goto_charge"
DEFAULT_DOCKED_STATUS = "charging,chargecompleted,charge_done,charging_dock"
DEFAULT_MODES = "smart,wall_follow,spiral,single"
DEFAULT_FAN_SPEEDS = "low,normal,high"
DEFAULT_PAUSED_STATE = "paused"
DEFAULT_RETURN_MODE = "chargego"
DEFAULT_STOP_STATUS = "standby"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_POWERGO_DP): col_to_select(dps, is_dps=True),
        vol.Required(CONF_IDLE_STATUS_VALUE, default=DEFAULT_IDLE_STATUS): str,
        vol.Required(CONF_DOCKED_STATUS_VALUE, default=DEFAULT_DOCKED_STATUS): str,
        vol.Optional(
            CONF_RETURNING_STATUS_VALUE, default=DEFAULT_RETURNING_STATUS
        ): str,
        vol.Optional(CONF_PAUSED_STATE, default=DEFAULT_PAUSED_STATE): str,
        vol.Optional(CONF_STOP_STATUS, default=DEFAULT_STOP_STATUS): str,
        vol.Optional(CONF_PAUSE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_BATTERY_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MODES, default=DEFAULT_MODES): str,
        vol.Optional(CONF_RETURN_MODE, default=DEFAULT_RETURN_MODE): str,
        vol.Optional(CONF_FAN_SPEED_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_SPEEDS, default=DEFAULT_FAN_SPEEDS): str,
        vol.Optional(CONF_CLEAN_TIME_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CLEAN_AREA_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CLEAN_RECORD_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_LOCATE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAULT_DP): col_to_select(dps, is_dps=True),
    }


class LocalTuyaVacuum(LocalTuyaEntity, StateVacuumEntity):
    """Tuya vacuum device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocalTuyaVacuum."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._battery_level = None
        self._attrs = {}

        self._idle_status_list = []
        if self.has_config(CONF_IDLE_STATUS_VALUE):
            status = self._config[CONF_IDLE_STATUS_VALUE].split(",")
            self._idle_status_list = [state.lstrip() for state in status]

        self._modes_list = []
        if self.has_config(CONF_MODES):
            modes_list = self._config[CONF_MODES].split(",")
            self._modes_list = [mode.lstrip() for mode in modes_list]
            self._attrs[MODES_LIST] = self._modes_list

        self._returning_status_list = []
        if self.has_config(CONF_RETURNING_STATUS_VALUE):
            returning_status = self._config[CONF_RETURNING_STATUS_VALUE].split(",")
            self._returning_status_list = [state.lstrip() for state in returning_status]

        self._docked_status_list = []
        if self.has_config(CONF_DOCKED_STATUS_VALUE):
            docked_status = self._config[CONF_DOCKED_STATUS_VALUE].split(",")
            self._docked_status_list = [state.lstrip() for state in docked_status]

        self._fan_speed_list = []
        if self.has_config(CONF_FAN_SPEEDS):
            fan_speeds = self._config[CONF_FAN_SPEEDS].split(",")
            self._fan_speed_list = [speed.lstrip() for speed in fan_speeds]

        self._fan_speed = ""
        self._cleaning_mode = ""

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Flag supported features."""
        supported_features = (
            VacuumEntityFeature.START
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.STATUS
            | VacuumEntityFeature.STATE
        )

        if (
            self.has_config(CONF_RETURN_MODE)
            and self._config[CONF_RETURN_MODE] in self._modes_list
        ):
            supported_features |= VacuumEntityFeature.RETURN_HOME
        if self.has_config(CONF_FAN_SPEED_DP):
            supported_features |= VacuumEntityFeature.FAN_SPEED
        if self.has_config(CONF_BATTERY_DP):
            supported_features |= VacuumEntityFeature.BATTERY
        if self.has_config(CONF_LOCATE_DP):
            supported_features |= VacuumEntityFeature.LOCATE

        return supported_features

    @property
    def activity(self) -> VacuumActivity | None:
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

    async def async_stop(self, **kwargs):
        """Turn the vacuum off stopping the cleaning."""
        if (
            self.has_config(CONF_STOP_STATUS)
            and self._config[CONF_STOP_STATUS] in self._modes_list
        ):
            await self._device.set_dp(
                self._config[CONF_STOP_STATUS], self._config[CONF_MODE_DP]
            )
        else:
            await self._device.set_dp(False, self._config[CONF_POWERGO_DP])
            # _LOGGER.error("Missing command for stop in commands set.")

    async def async_pause(self, **kwargs):
        """Stop the vacuum cleaner, do not return to base."""
        if self.has_config(CONF_PAUSE_DP):
            return await self._device.set_dp(True, self._config[CONF_PAUSE_DP])

        await self.async_stop()

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        if self.has_config(CONF_RETURN_MODE):
            await self._device.set_dp(
                self._config[CONF_RETURN_MODE], self._config[CONF_MODE_DP]
            )
        else:
            _LOGGER.error("Missing command for return home in commands set.")

    async def async_clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        return None

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        if self.has_config(CONF_LOCATE_DP):
            await self._device.set_dp(True, self._config[CONF_LOCATE_DP])

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
        state_value = self.dp_value(self._dp_id)

        if state_value is None:
            self._state = None
        elif state_value in self._idle_status_list:
            self._state = VacuumActivity.IDLE
        elif state_value in self._docked_status_list:
            self._state = VacuumActivity.DOCKED
        elif state_value in self._returning_status_list:
            self._state = VacuumActivity.RETURNING
        elif state_value in [self._config[CONF_PAUSED_STATE], "pause"] or (
            self.dp_value(CONF_PAUSE_DP) is True
        ):
            self._state = VacuumActivity.PAUSED
        else:
            self._state = VacuumActivity.CLEANING

        if self.has_config(CONF_BATTERY_DP):
            self._battery_level = self.dp_value(CONF_BATTERY_DP)

        self._cleaning_mode = ""
        if self.has_config(CONF_MODES):
            self._cleaning_mode = self.dp_value(CONF_MODE_DP)
            self._attrs[MODE] = self._cleaning_mode

        self._fan_speed = ""
        if self.has_config(CONF_FAN_SPEEDS):
            self._fan_speed = self.dp_value(CONF_FAN_SPEED_DP)

        if self.has_config(CONF_CLEAN_TIME_DP):
            self._attrs[CLEAN_TIME] = self.dp_value(CONF_CLEAN_TIME_DP)

        if self.has_config(CONF_CLEAN_AREA_DP):
            self._attrs[CLEAN_AREA] = self.dp_value(CONF_CLEAN_AREA_DP)

        if self.has_config(CONF_CLEAN_RECORD_DP):
            self._attrs[CLEAN_RECORD] = self.dp_value(CONF_CLEAN_RECORD_DP)

        if self.has_config(CONF_FAULT_DP):
            self._attrs[FAULT] = self.dp_value(CONF_FAULT_DP)
            if self._attrs[FAULT] != 0:
                self._state = VacuumActivity.ERROR


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaVacuum, flow_schema)
