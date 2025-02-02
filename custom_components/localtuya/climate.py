"""Platform to locally control Tuya-based climate devices.
    # PRESETS and HVAC_MODE Needs to be handle in better way.
"""

import asyncio
import logging
from functools import partial
from .config_flow import _col_to_select
from homeassistant.helpers import selector

import voluptuous as vol
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    HVACAction,
    HVACMode,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    ClimateEntityFeature,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_TOP,
    SWING_ON,
    SWING_OFF,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfTemperature,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_ECO_DP,
    CONF_ECO_VALUE,
    CONF_HEURISTIC_ACTION,
    CONF_HVAC_ACTION_DP,
    CONF_HVAC_ACTION_SET,
    CONF_HVAC_MODE_DP,
    CONF_HVAC_MODE_SET,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_MAX_TEMP_DP,
    CONF_MIN_TEMP_DP,
    CONF_PRECISION,
    CONF_PRESET_DP,
    CONF_PRESET_SET,
    CONF_TARGET_PRECISION,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_TEMPERATURE_STEP,
    CONF_HVAC_FAN_MODE_DP,
    CONF_HVAC_FAN_MODE_SET,
    CONF_HVAC_SWING_MODE_DP,
    CONF_HVAC_SWING_MODE_SET,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_HVAC_ADD_OFF,
    CONF_FAN_SPEED_DP,
    CONF_FAN_SPEED_LIST,
)

_LOGGER = logging.getLogger(__name__)


HVAC_OFF = {HVACMode.OFF.value: "off"}
RENAME_HVAC_MODE_SETS = {  # Migrate to 3
    ("manual", "Manual", "hot", "m", "True"): HVACMode.HEAT.value,
    ("auto", "0", "p", "Program"): HVACMode.AUTO.value,
    ("freeze", "cold", "1"): HVACMode.COOL.value,
    ("wet"): HVACMode.DRY.value,
}
RENAME_ACTION_SETS = {  # Migrate to 3
    ("open", "opened", "heating", "Heat", "True"): HVACAction.HEATING.value,
    ("closed", "close", "no_heating"): HVACAction.IDLE.value,
    ("Warming", "warming", "False"): HVACAction.IDLE.value,
    ("cooling"): HVACAction.COOLING.value,
    ("off"): HVACAction.OFF.value,
}
RENAME_PRESET_SETS = {
    "Holiday": (PRESET_AWAY),
    "Program": (PRESET_HOME),
    "Manual": (PRESET_NONE, "manual"),
    "Auto": "auto",
    "Manual": "manual",
    "Smart": "smart",
    "Comfort": "comfortable",
    "ECO": "eco",
}


HVAC_MODE_SETS = {
    HVACMode.OFF: False,
    HVACMode.AUTO: "auto",
    HVACMode.COOL: "cold",
    HVACMode.HEAT: "hot",
    HVACMode.HEAT_COOL: "heat",
    HVACMode.DRY: "wet",
    HVACMode.FAN_ONLY: "wind",
}

HVAC_ACTION_SETS = {
    "True/False": {
        HVACAction.HEATING: True,
        HVACAction.IDLE: False,
    },
    "open/close": {
        HVACAction.HEATING: "open",
        HVACAction.IDLE: "close",
    },
    "opened/closed": {
        HVACAction.HEATING: "opened",
        HVACAction.IDLE: "closed",
    },
    "heating/no_heating": {
        HVACAction.HEATING: "heating",
        HVACAction.IDLE: "no_heating",
    },
    "heating/cooling": {
        HVACAction.HEATING: "heating",
        HVACAction.COOLING: "cooling",
        HVACAction.IDLE: "ventilation",
        HVACAction.OFF: "off",
    },
    "Heat/Warming": {
        HVACAction.HEATING: "Heat",
        HVACAction.IDLE: "Warming",
    },
    "heating/warming": {
        HVACAction.HEATING: "heating",
        HVACAction.IDLE: "warming",
    },
}
HVAC_FAN_MODE_SETS = {
    "Auto/Low/Middle/High/Strong": {
        FAN_AUTO: "auto",
        FAN_LOW: "low",
        FAN_MEDIUM: "middle",
        FAN_HIGH: "high",
        FAN_TOP: "strong",
    }
}
HVAC_SWING_MODE_SETS = {
    "True/False": {
        SWING_ON: True,
        SWING_OFF: False,
    }
}
PRESET_SETS = {
    "Manual/Holiday/Program": {
        PRESET_AWAY: "Holiday",
        PRESET_HOME: "Program",
        PRESET_NONE: "Manual",
    },
    "smart/holiday/hold": {
        PRESET_AWAY: "holiday",
        PRESET_HOME: "smart",
        PRESET_NONE: "hold",
    },
    "auto/smart": {
        "auto": "Auto",
        "smart": "Smart",
    },
    "auto/manual/smart/comfortable/eco": {
        "auto": "Auto",
        "manual": "Manual",
        "smart": "Smart",
        "comfortable": "Comfort",
        "eco": "ECO",
    },
}


TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS
DEFAULT_PRECISION = PRECISION_TENTHS
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES
# Empirically tested to work for AVATTO thermostat
MODE_WAIT = 0.1

FAN_SPEEDS_DEFAULT = "auto,low,middle,high"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TEMPERATURE_STEP, default=PRECISION_WHOLE): _col_to_select(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_TEMP_MIN, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TEMP_MAX, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MIN_TEMP_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_PRECISION, default=PRECISION_WHOLE): _col_to_select(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(
            CONF_TARGET_PRECISION, default=str(DEFAULT_PRECISION)
        ): _col_to_select([PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]),
        vol.Optional(CONF_HVAC_MODE_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_FAN_MODE_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_FAN_MODE_SET): _col_to_select(list(HVAC_FAN_MODE_SETS.keys())),
        vol.Optional(
            CONF_HVAC_MODE_SET, default=HVAC_MODE_SETS
        ): selector.ObjectSelector(),
        vol.Optional(CONF_HVAC_ACTION_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(
            CONF_HVAC_ACTION_SET, default=HVAC_ACTION_SETS
        ): selector.ObjectSelector(),
        vol.Optional(CONF_ECO_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_ECO_VALUE): str,
        vol.Optional(CONF_PRESET_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_PRESET_SET, default={}): selector.ObjectSelector(),
        vol.Optional(CONF_FAN_SPEED_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_SPEED_LIST, default=FAN_SPEEDS_DEFAULT): str,
        vol.Optional(CONF_TEMPERATURE_UNIT): _col_to_select(
            [TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT]
        ),
        vol.Optional(CONF_TARGET_PRECISION, default=PRECISION_WHOLE): _col_to_select(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_HVAC_ADD_OFF, default=True): bool,
        vol.Optional(CONF_HEURISTIC_ACTION): bool,
    }


class LocalTuyaClimate(LocalTuyaEntity, ClimateEntity):
    """Tuya climate device."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocalTuyaClimate."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._target_temperature = None
        self._current_temperature = None
        self._hvac_mode = None
        self._fan_mode = None
        self._swing_mode = None
        self._preset_mode = None
        self._hvac_action = None
        self._precision = float(self._config.get(CONF_PRECISION, DEFAULT_PRECISION))
        self._conf_hvac_mode_dp = self._config.get(CONF_HVAC_MODE_DP)
        self._conf_hvac_fan_mode_dp = self._config.get(CONF_HVAC_FAN_MODE_DP)
        self._conf_hvac_fan_mode_set = HVAC_FAN_MODE_SETS.get(
            self._config.get(CONF_HVAC_FAN_MODE_SET), {}
        )
        self._conf_hvac_swing_mode_dp = self._config.get(CONF_HVAC_SWING_MODE_DP)
        self._conf_hvac_swing_mode_set = HVAC_SWING_MODE_SETS.get(
            self._config.get(CONF_HVAC_SWING_MODE_SET), {}
        )
        self._precision_target = float(
            self._config.get(CONF_TARGET_PRECISION, DEFAULT_PRECISION)
        )

        # HVAC Modes
        if modes_set := self._config.get(CONF_HVAC_MODE_SET, {}):
            # HA HVAC Modes are all lower case.
            modes_set = {k.lower(): v for k, v in modes_set.copy().items()}
        self._hvac_mode_set = modes_set

        # Presets
        self._preset_dp = self._config.get(CONF_PRESET_DP)
        self._preset_set: dict = self._config.get(CONF_PRESET_SET, {})

        # Sort Modes If the HVAC isn't supported by HA then we add it as preset.
        if self._preset_dp == self._hvac_mode_dp or not self._preset_dp:
            for k, v in self._hvac_mode_set.copy().items():
                if k not in HVACMode:
                    self._preset_dp = self._hvac_mode_dp
                    self._preset_set[k] = self._hvac_mode_set.pop(k)

        self._preset_name_to_value = {v: k for k, v in self._preset_set.items()}

        # HVAC Actions
        self._conf_hvac_action_dp = self._config.get(CONF_HVAC_ACTION_DP)
        if actions_set := self._config.get(CONF_HVAC_ACTION_SET, {}):
            actions_set = {k.lower(): v for k, v in actions_set.copy().items()}
        self._conf_hvac_action_set = actions_set

        # Fan
        self._fan_speed_dp = self._config.get(CONF_FAN_SPEED_DP)
        if fan_speeds := self._config.get(CONF_FAN_SPEED_LIST, []):
            fan_speeds = [v.lstrip() for v in fan_speeds.split(",")]
        self._fan_supported_speeds = fan_speeds
        self._has_fan_mode = self._fan_speed_dp and self._fan_supported_speeds

        # Eco!?
        self._eco_dp = self._config.get(CONF_ECO_DP)
        self._eco_value = self._config.get(CONF_ECO_VALUE, "ECO")
        self._has_presets = self._eco_dp or (self._preset_dp and self._preset_set)

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            supported_features = supported_features | ClimateEntityFeature.TARGET_TEMPERATURE
        if self.has_config(CONF_MAX_TEMP_DP):
            supported_features = supported_features | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if self.has_config(CONF_PRESET_DP) or self.has_config(CONF_ECO_DP):
            supported_features = supported_features | ClimateEntityFeature.PRESET_MODE
        if self.has_config(CONF_HVAC_FAN_MODE_DP) and self.has_config(CONF_HVAC_FAN_MODE_SET):
            supported_features = supported_features | ClimateEntityFeature.FAN_MODE
        if self.has_config(CONF_HVAC_SWING_MODE_DP):
            supported_features = supported_features | ClimateEntityFeature.SWING_MODE
        if self.has_config(CONF_PRESET_DP) or self.has_config(CONF_ECO_DP):
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self._has_presets:
            supported_features |= ClimateEntityFeature.PRESET_MODE
        if self._has_fan_mode:
            supported_features |= ClimateEntityFeature.FAN_MODE

        try:  # requires HA >= 2024.2.1
            supported_features |= ClimateEntityFeature.TURN_OFF
            supported_features |= ClimateEntityFeature.TURN_ON
        except AttributeError:
            ...

        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        # Unit may rely on self.hass.config.units.temperature_unit [System Unit]
        if self._config.get(CONF_TEMPERATURE_UNIT) == TEMPERATURE_FAHRENHEIT:
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        # DEFAULT_MIN_TEMP is in C
        return self._config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        # DEFAULT_MAX_TEMP is in C
        return self._config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
>>>>>>> 7a607a65087c9f88dc5f47d10678433d890afda3

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        if not self._state:
            return HVACMode.OFF

        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        if not self.has_config(CONF_HVAC_MODE_DP):
            return None

        modes = list(self._hvac_mode_set)

        if self._config.get(CONF_HVAC_ADD_OFF, True) and HVACMode.OFF not in modes:
            modes.append(HVACMode.OFF)
        return modes

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if not self._state:
            return HVACAction.OFF

        if not self._conf_hvac_action_dp:
            if self._hvac_mode == HVACMode.COOL:
                self._hvac_action = HVACAction.COOLING
            if self._hvac_mode == HVACMode.HEAT:
                self._hvac_action = HVACAction.HEATING
            if self._hvac_mode == HVACMode.DRY:
                self._hvac_action = HVACAction.DRYING

        # This exists from upstream, not sure the use case of this.
        if self._config.get(CONF_HEURISTIC_ACTION, False):
            if self._hvac_mode == HVACMode.HEAT:
                if self._current_temperature < (
                    self._target_temperature - self._precision
                ):
                    self._hvac_action = HVACMode.HEAT
                if self._current_temperature == (
                    self._target_temperature - self._precision
                ):
                    if self._hvac_action == HVACMode.HEAT:
                        self._hvac_action = HVACMode.HEAT
                    if self._hvac_action == HVACAction.IDLE:
                        self._hvac_action = HVACAction.IDLE
                if (
                    self._current_temperature + self._precision
                ) > self._target_temperature:
                    self._hvac_action = HVACAction.IDLE
            return self._hvac_action
        return self._hvac_action

    @property
    def preset_mode(self):
        """Return current preset."""
        mode = self.dp_value(CONF_HVAC_MODE_DP)
        if mode in list(self._hvac_mode_set.values()):
            return None

        return self._preset_mode

    @property
    def preset_modes(self):
        """Return the list of available presets modes."""
        if not self._has_presets:
            return None

        presets = list(self._preset_set.values())
        if self._eco_dp:
            presets.append(PRESET_ECO)
        return presets

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        target_step = self._config.get(CONF_TEMPERATURE_STEP, DEFAULT_TEMPERATURE_STEP)
        return float(target_step)

    @property
    def fan_mode(self):
        """Return the fan setting."""
        if not (fan_value := self.dp_value(self._fan_speed_dp)):
            return None
        return fan_value

    @property
    def fan_modes(self) -> list:
        """Return the list of available fan modes."""
        return list(self._conf_hvac_fan_mode_set)

    @property
    def swing_mode(self):
        """Return the swing setting."""
        return self._swing_mode

    @property
    def swing_modes(self):
        """Return the list of available swing modes."""
        if not self.has_config(CONF_HVAC_SWING_MODE_DP):
            return None
        return list(self._conf_hvac_swing_mode_set)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self.has_config(CONF_TARGET_TEMPERATURE_DP):
            temperature = round(kwargs[ATTR_TEMPERATURE] / self._precision_target)
            await self._device.set_dp(
                temperature, self._config[CONF_TARGET_TEMPERATURE_DP]
            )

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if not self._state:
            await self._device.set_dp(True, self._dp_id)

        await self._device.set_dp(fan_mode, self._fan_speed_dp)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        new_states = {self._dp_id: hvac_mode != HVACMode.OFF}
        if hvac_mode in self._hvac_mode_set:
            new_states[self._hvac_mode_dp] = self._hvac_mode_set[hvac_mode]

        await self._device.set_dps(new_states)

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        if self._conf_hvac_swing_mode_dp is None:
            _LOGGER.error("Swing mode unsupported (no DP)")
            return
        if swing_mode not in self._conf_hvac_swing_mode_set:
            _LOGGER.error("Unsupported swing_mode: %s" % swing_mode)
            return
        await self._device.set_dp(
            self._conf_hvac_swing_mode_set[swing_mode], self._conf_hvac_swing_mode_dp
        )

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.set_dp(True, self._dp_id)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.set_dp(False, self._dp_id)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if preset_mode == PRESET_ECO:
            await self._device.set_dp(self._eco_value, self._eco_dp)
            return

        preset_value = self._preset_name_to_value.get(preset_mode)
        await self._device.set_dp(preset_value, self._preset_dp)

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if _min_temp := self._config.get(CONF_MIN_TEMP_DP):
            return self.dps_conf(CONF_MIN_TEMP_DP)
        if self.has_config(CONF_TEMP_MIN):
            return self._config[CONF_TEMP_MIN]
        # DEFAULT_MIN_TEMP is in C
        if self.temperature_unit == TEMP_FAHRENHEIT:
            return DEFAULT_MIN_TEMP * 1.8 + 32
        else:
            return DEFAULT_MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        if self.has_config(CONF_MAX_TEMP_DP):
            return self.dps_conf(CONF_MAX_TEMP_DP)
        if self.has_config(CONF_TEMP_MAX):
            return self._config[CONF_TEMP_MAX]
        # DEFAULT_MAX_TEMP is in C
        if self.temperature_unit == TEMP_FAHRENHEIT:
            return DEFAULT_MAX_TEMP * 1.8 + 32
        else:
            return DEFAULT_MAX_TEMP

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dp_value(self._dp_id)

        # Update target temperature
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            self._target_temperature = (
                self.dp_value(CONF_TARGET_TEMPERATURE_DP) * self._precision_target
            )

        # Update current temperature
        if self.has_config(CONF_CURRENT_TEMPERATURE_DP):
            self._current_temperature = (
                self.dp_value(CONF_CURRENT_TEMPERATURE_DP) * self._precision
            )

        # Update preset states
        if self._has_presets:
            if self.dp_value(CONF_ECO_DP) == self._eco_value:
                self._preset_mode = PRESET_ECO
            else:
                for preset_value, preset_name in self._preset_set.items():
                    if self.dp_value(CONF_PRESET_DP) == preset_value:
                        self._preset_mode = preset_name
                        break
                else:
                    self._preset_mode = PRESET_NONE

        # If device is off there is no needs to check the states.
        if not self._state:
            return

        # Update the HVAC Mode
        if self.has_config(CONF_HVAC_MODE_DP):
            for ha_hvac, tuya_value in self._hvac_mode_set.items():
                if self.dp_value(CONF_HVAC_MODE_DP) == tuya_value:
                    self._hvac_mode = ha_hvac
                    break

        # Update the fan status
        if self.has_config(CONF_HVAC_FAN_MODE_DP):
            for mode, value in self._conf_hvac_fan_mode_set.items():
                if self.dps_conf(CONF_HVAC_FAN_MODE_DP) == value:
                    self._fan_mode = mode
                    break
            else:
                # in case fan mode and preset share the same dp
                _LOGGER.debug("Unknown fan mode %s" % self.dps_conf(CONF_HVAC_FAN_MODE_DP))
                self._fan_mode = FAN_AUTO

        # Update the swing status
        if self.has_config(CONF_HVAC_SWING_MODE_DP):
            for mode, value in self._conf_hvac_swing_mode_set.items():
                if self.dps_conf(CONF_HVAC_SWING_MODE_DP) == value:
                    self._swing_mode = mode
                    break
            else:
                _LOGGER.debug("Unknown swing mode %s" % self.dps_conf(CONF_HVAC_SWING_MODE_DP))
                self._swing_mode = SWING_OFF

        # Update the current action
        if self.has_config(CONF_HVAC_ACTION_DP):
            for ha_action, tuya_value in self._conf_hvac_action_set.items():
                if self.dp_value(CONF_HVAC_ACTION_DP) == tuya_value:
                    self._hvac_action = ha_action
                    break


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaClimate, flow_schema)
