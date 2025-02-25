"""Platform to locally control Tuya-based climate devices."""

import asyncio
from enum import StrEnum
import logging
from functools import partial
from .config_flow import col_to_select
from homeassistant.helpers.selector import ObjectSelector

import voluptuous as vol
from homeassistant.components.climate import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    PRESET_AWAY,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    ClimateEntityFeature,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    UnitOfTemperature,
)
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
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
    CONF_SWING_MODE_DP,
    CONF_SWING_MODES,
    CONF_SWING_HORIZONTAL_DP,
    CONF_SWING_HORIZONTAL_MODES,
)

_LOGGER = logging.getLogger(__name__)


HVAC_OFF = {HVACMode.OFF.value: "off"}  # Migrate to 3
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
RENAME_PRESET_SETS = {  # Migrate to 3
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


class SupportedTemps(StrEnum):
    C = "celsius"
    F = "fahrenheit"
    C_F = f"celsius/fahrenheit"
    F_C = f"fahrenheit/celsius"


SUPPORTED_TEMPERATURES = {
    UnitOfTemperature.CELSIUS: SupportedTemps.C,
    UnitOfTemperature.FAHRENHEIT: SupportedTemps.F,
    f"Target Temperature: {UnitOfTemperature.CELSIUS} | Current Temperature {UnitOfTemperature.FAHRENHEIT}": SupportedTemps.C_F,
    f"Current Temperature {UnitOfTemperature.CELSIUS} | Target Temperature: {UnitOfTemperature.FAHRENHEIT} ": SupportedTemps.F_C,
}
SUPPORTED_PRECISIONS = [0.01, PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]

DEFAULT_TEMPERATURE_UNIT = SupportedTemps.C
DEFAULT_PRECISION = PRECISION_TENTHS
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES
# Empirically tested to work for AVATTO thermostat
MODE_WAIT = 0.1

FAN_SPEEDS_DEFAULT = "auto,low,middle,high"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TEMPERATURE_STEP, default=PRECISION_WHOLE): col_to_select(
            SUPPORTED_PRECISIONS
        ),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MIN_TEMP_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_PRECISION, default=str(DEFAULT_PRECISION)): col_to_select(
            SUPPORTED_PRECISIONS
        ),
        vol.Optional(
            CONF_TARGET_PRECISION, default=str(DEFAULT_PRECISION)
        ): col_to_select(SUPPORTED_PRECISIONS),
        vol.Optional(CONF_HVAC_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_FAN_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_MODE_SET, default=HVAC_MODE_SETS): ObjectSelector(),
        vol.Optional(CONF_HVAC_ACTION_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HVAC_ACTION_SET, default=HVAC_ACTION_SETS): ObjectSelector(),
        vol.Optional(CONF_ECO_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_ECO_VALUE): str,
        vol.Optional(CONF_PRESET_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_PRESET_SET, default={}): ObjectSelector(),
        vol.Optional(CONF_SWING_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SWING_MODES, default={}): ObjectSelector(),
        vol.Optional(CONF_SWING_HORIZONTAL_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SWING_HORIZONTAL_MODES, default={}): ObjectSelector(),
        vol.Optional(CONF_FAN_SPEED_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_FAN_SPEED_LIST, default=FAN_SPEEDS_DEFAULT): str,
        vol.Optional(CONF_TARGET_PRECISION, default=PRECISION_WHOLE): col_to_select(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
        vol.Optional(CONF_HVAC_ADD_OFF, default=True): bool,
        vol.Optional(CONF_TEMPERATURE_UNIT): col_to_select(SUPPORTED_TEMPERATURES),
        vol.Optional(CONF_HEURISTIC_ACTION): bool,
    }


# Converters
def f_to_c(num):
    return (num - 32) * 5 / 9 if num else num


def c_to_f(num):
    return (num * 1.8) + 32 if num else num


def config_unit(unit):
    if unit == SupportedTemps.F:
        return UnitOfTemperature.FAHRENHEIT
    else:
        return UnitOfTemperature.CELSIUS


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
        self._state_on, self._state_off = True, False
        self._target_temperature = None
        self._target_temp_forced_to_celsius = None
        self._current_temperature = None
        self._hvac_mode = None
        self._fan_mode = None
        self._swing_mode = None
        self._preset_mode = None
        self._hvac_action = None
        self._precision = float(self._config.get(CONF_PRECISION, DEFAULT_PRECISION))
        self._conf_hvac_fan_mode_dp = self._config.get(CONF_HVAC_FAN_MODE_DP)
        self._conf_hvac_swing_mode_dp = self._config.get(CONF_HVAC_SWING_MODE_DP)
        self._precision_target = float(
            self._config.get(CONF_TARGET_PRECISION, DEFAULT_PRECISION)
        )

        # HVAC Modes
        self._hvac_mode_dp = self._config.get(CONF_HVAC_MODE_DP)
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

        # Swing configurations.
        self._swing_mode_dp = self._config.get(CONF_SWING_MODE_DP)
        self._swing_modes = self._config.get(CONF_SWING_MODES, {})
        self._swing_v_name = {v: k for k, v in self._swing_modes.items()}

        self._swing_horizontal_mode_dp = self._config.get(CONF_SWING_HORIZONTAL_DP)
        self._swing_horizontal_modes = self._config.get(CONF_SWING_HORIZONTAL_MODES, {})
        self._swing_h_name = {v: k for k, v in self._swing_horizontal_modes.items()}

        # Eco!?
        self._eco_dp = self._config.get(CONF_ECO_DP)
        self._eco_value = self._config.get(CONF_ECO_VALUE, "ECO")
        self._has_presets = self._eco_dp or (self._preset_dp and self._preset_set)

        self._min_temp = self._config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
        self._max_temp = self._config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)

        # Temperature unit
        config_temp_unit = self._config.get(CONF_TEMPERATURE_UNIT, "")
        target_unit, *current_unit = config_temp_unit.split("/")
        set_temp_unit = UnitOfTemperature.CELSIUS
        if current_unit:
            self._target_temp_forced_to_celsius = target_unit == SupportedTemps.F
            if self._target_temp_forced_to_celsius:
                self._min_temp = f_to_c(self._min_temp)
                self._max_temp = f_to_c(self._max_temp)
        else:
            set_temp_unit = config_unit(config_temp_unit)
        self._temperature_unit = set_temp_unit

    @property
    def _is_on(self):
        """Return if the device is on."""
        return self._state and self._state != self._state_off

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = ClimateEntityFeature(0)
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if self._has_presets:
            supported_features |= ClimateEntityFeature.PRESET_MODE
        if self._fan_speed_dp and self._fan_supported_speeds:
            supported_features |= ClimateEntityFeature.FAN_MODE
        if self._swing_modes and self._swing_modes:
            supported_features |= ClimateEntityFeature.SWING_MODE
        if self._swing_horizontal_mode_dp and self._swing_horizontal_modes:
            supported_features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE

        supported_features |= ClimateEntityFeature.TURN_OFF
        supported_features |= ClimateEntityFeature.TURN_ON

        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return self._temperature_unit

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        # DEFAULT_MIN_TEMP is in C
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        # DEFAULT_MAX_TEMP is in C
        return self._max_temp

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        if not self._is_on:
            return HVACMode.OFF
        if not self._hvac_mode_dp:
            return HVACMode.HEAT

        return self._hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        if not self.has_config(CONF_HVAC_MODE_DP):
            return [HVACMode.OFF]

        modes = list(self._hvac_mode_set)

        if self._config.get(CONF_HVAC_ADD_OFF, True) and HVACMode.OFF not in modes:
            modes.append(HVACMode.OFF)
        return modes

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported."""
        if not self._is_on:
            return HVACAction.OFF

        hvac_action = self._hvac_action
        hvac_mode = self._hvac_mode

        if (
            (self._config.get(CONF_HEURISTIC_ACTION) or not self._conf_hvac_action_dp)
            and (target_temperature := self._target_temperature) is not None
            and (current_temperature := self._current_temperature) is not None
        ):
            # This function assumes that action changes based on target step different from current.
            target_step = self.target_temperature_step
            is_heating = current_temperature < (target_temperature - target_step)
            is_cooling = current_temperature > (target_temperature + target_step)

            if hvac_mode == HVACMode.HEAT:
                if is_heating:
                    hvac_action = HVACAction.HEATING
                elif current_temperature >= target_temperature:
                    hvac_action = HVACAction.IDLE
            elif hvac_mode == HVACMode.COOL:
                if is_cooling:
                    hvac_action = HVACAction.COOLING
                elif current_temperature <= target_temperature:
                    hvac_action = HVACAction.IDLE
            elif hvac_mode == HVACMode.HEAT_COOL:
                if is_heating:
                    hvac_action = HVACAction.HEATING
                elif is_cooling:
                    hvac_action = HVACAction.COOLING
                elif current_temperature == target_temperature:
                    hvac_action = HVACAction.IDLE
            elif hvac_mode == HVACMode.DRY:
                hvac_action = HVACAction.DRYING
            elif hvac_mode == HVACMode.FAN_ONLY:
                hvac_action = HVACAction.FAN

            self._hvac_action = hvac_action

        return hvac_action

    @property
    def preset_mode(self):
        """Return current preset."""
        mode = self.dp_value(CONF_HVAC_MODE_DP)
        if self._preset_dp == self._hvac_mode_dp and (
            mode in list(self._hvac_mode_set.values())
        ):
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
        return self._fan_supported_speeds

    @property
    def swing_mode(self):
        """Return the swing setting."""
        return self._swing_mode

    def swing_modes(self) -> list[str] | None:
        """Return the list of available swing modes."""
        return list(self._swing_modes.values())

    @property
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return the list of available horizontal swing modes."""
        return list(self._swing_horizontal_modes.values())

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        await self._device.set_dp(self._swing_v_name[swing_mode], self._swing_mode_dp)

    async def async_set_swing_horizontal_mode(self, swing_mode):
        """Set new target horizontal swing operation."""
        await self._device.set_dp(
            self._swing_h_name[swing_mode], self._swing_horizontal_mode_dp
        )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self.has_config(CONF_TARGET_TEMPERATURE_DP):
            temperature = kwargs[ATTR_TEMPERATURE]

            if self._target_temp_forced_to_celsius:
                # Revert Temperature to Fahrenheit it was forced to celsius
                temperature = round(c_to_f(temperature))

            temperature = round(temperature / self._precision_target)
            await self._device.set_dp(
                temperature, self._config[CONF_TARGET_TEMPERATURE_DP]
            )

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if not self._is_on:
            await self._device.set_dp(self._state_on, self._dp_id)

        await self._device.set_dp(fan_mode, self._fan_speed_dp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target operation mode."""
        new_states = {}
        if not self._is_on:
            new_states[self._dp_id] = self._state_on
        elif hvac_mode == HVACMode.OFF and HVACMode.OFF not in self._hvac_mode_set:
            new_states[self._dp_id] = self._state_off

        if hvac_mode in self._hvac_mode_set:
            new_states[self._hvac_mode_dp] = self._hvac_mode_set[hvac_mode]

        await self._device.set_dps(new_states)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.set_dp(self._state_on, self._dp_id)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.set_dp(self._state_off, self._dp_id)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if preset_mode == PRESET_ECO:
            await self._device.set_dp(self._eco_value, self._eco_dp)
            return

        preset_value = self._preset_name_to_value.get(preset_mode)
        await self._device.set_dp(preset_value, self._preset_dp)

    def connection_made(self):
        """The connection has made with the device and status retrieved. configure entity based on it."""
        super().connection_made()

        match self.dp_value(self._dp_id):
            case str() as v if v.lower() in ("on", "off"):
                self._state_on = "ON" if v.isupper() else "on"
                self._state_off = "OFF" if v.isupper() else "off"
            case int() as v if not isinstance(v, bool) and v in (0, 1):
                self._state_on = 1
                self._state_off = 0

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dp_value(self._dp_id)

        # Update target temperature
        if self.has_config(CONF_TARGET_TEMPERATURE_DP) and (
            target_dp_value := self.dp_value(CONF_TARGET_TEMPERATURE_DP)
        ):
            self._target_temperature = target_dp_value * self._precision_target

        # Update current temperature
        if self.has_config(CONF_CURRENT_TEMPERATURE_DP) and (
            current_dp_temp := self.dp_value(CONF_CURRENT_TEMPERATURE_DP)
        ):
            self._current_temperature = current_dp_temp * self._precision

        # Force the Current temperature and Target temperature to matching the unit.
        if self._target_temp_forced_to_celsius:
            self._target_temperature = f_to_c(self._target_temperature)
        elif self._target_temp_forced_to_celsius is False:
            self._current_temperature = f_to_c(self._current_temperature)

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
        if not self._is_on:
            return

        # Update the HVAC Mode
        if self.has_config(CONF_HVAC_MODE_DP):
            for ha_hvac, tuya_value in self._hvac_mode_set.items():
                if self.dp_value(CONF_HVAC_MODE_DP) == tuya_value:
                    self._hvac_mode = ha_hvac
                    break

        # Update the current action
        if self.has_config(CONF_HVAC_ACTION_DP):
            for ha_action, tuya_value in self._conf_hvac_action_set.items():
                if self.dp_value(CONF_HVAC_ACTION_DP) == tuya_value:
                    self._hvac_action = ha_action
                    break

        # Update swing actions
        if (swing_v := self.dp_value(self._swing_mode_dp)) is not None:
            self._attr_swing_mode = self._swing_modes.get(swing_v)
        if (swing_h := self.dp_value(self._swing_horizontal_mode_dp)) is not None:
            self._attr_swing_horizontal_mode = self._swing_horizontal_modes.get(swing_h)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaClimate, flow_schema)
