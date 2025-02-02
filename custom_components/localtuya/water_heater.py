"""Platform to locally control Tuya-based WaterHeater devices."""

import logging
from functools import partial
from .config_flow import col_to_select
from homeassistant.helpers import selector

import voluptuous as vol
from homeassistant.components.water_heater import (
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DOMAIN,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.components.water_heater.const import (
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_PERFORMANCE,
    STATE_HIGH_DEMAND,
    STATE_HEAT_PUMP,
    STATE_GAS,
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
    CONF_TARGET_TEMPERATURE_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_PRECISION,
    CONF_TARGET_PRECISION,
    CONF_MODE_DP,
    CONF_MODES,
    CONF_TARGET_TEMPERATURE_LOW_DP,
    CONF_TARGET_TEMPERATURE_HIGH_DP,
)

_LOGGER = logging.getLogger(__name__)


TEMPERATURE_CELSIUS = "celsius"
TEMPERATURE_FAHRENHEIT = "fahrenheit"

DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_CELSIUS
DEFAULT_PRECISION = PRECISION_TENTHS
DEFAULT_TEMPERATURE_STEP = PRECISION_HALVES
PERCISION_SET = [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]

OFF_MODE = "Off"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TARGET_TEMPERATURE_LOW_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_TARGET_TEMPERATURE_HIGH_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_PRECISION, default=str(DEFAULT_PRECISION)): col_to_select(
            PERCISION_SET
        ),
        vol.Optional(
            CONF_TARGET_PRECISION, default=str(DEFAULT_PRECISION)
        ): col_to_select(PERCISION_SET),
        vol.Optional(CONF_MODE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_MODES, default={}): selector.ObjectSelector(),
        vol.Optional(CONF_TEMPERATURE_UNIT): col_to_select(
            [TEMPERATURE_CELSIUS, TEMPERATURE_FAHRENHEIT]
        ),
    }


def config_unit(unit):
    if unit == TEMPERATURE_FAHRENHEIT:
        return UnitOfTemperature.FAHRENHEIT
    else:
        return UnitOfTemperature.CELSIUS


class LocalTuyaWaterHeater(LocalTuyaEntity, WaterHeaterEntity):
    """Tuya WaterHeater device."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocalTuyaWaterHeater."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None
        self._target_temperature = None
        self._current_temperature = None
        self._dp_mode = self._config.get(CONF_MODE_DP, None)

        self._available_modes = self._config.get(CONF_MODES, {})
        self._modes_name_to_value = {v: k for k, v in self._available_modes.items()}

        self._precision = float(self._config.get(CONF_PRECISION, DEFAULT_PRECISION))
        self._precision_target = float(
            self._config.get(CONF_TARGET_PRECISION, DEFAULT_PRECISION)
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = WaterHeaterEntityFeature(0)
        if self.has_config(CONF_TARGET_TEMPERATURE_DP):
            supported_features |= WaterHeaterEntityFeature.TARGET_TEMPERATURE
        if self.has_config(CONF_MODE_DP):
            supported_features |= WaterHeaterEntityFeature.OPERATION_MODE

        supported_features |= WaterHeaterEntityFeature.ON_OFF

        return supported_features

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._precision

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return config_unit(self._config.get(CONF_TEMPERATURE_UNIT))

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._config.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._config.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)

    @property
    def operation_list(self) -> list[str] | None:
        """Return the list of available operation modes."""
        return list(self._modes_name_to_value) + [OFF_MODE]

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_high(self) -> float | None:
        """Return the highbound target temperature we try to reach."""
        return self._attr_target_temperature_high

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lowbound target temperature we try to reach."""
        return self._attr_target_temperature_low

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs and self.has_config(CONF_TARGET_TEMPERATURE_DP):
            temperature = kwargs[ATTR_TEMPERATURE]

            temperature = round(temperature / self._precision_target)
            await self._device.set_dp(
                temperature, self._config[CONF_TARGET_TEMPERATURE_DP]
            )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        status = {}
        if operation_mode == OFF_MODE:
            return await self.async_turn_off()
        elif not self._state:
            status[self._dp_id] = True

        mode = self._modes_name_to_value.get(operation_mode)
        status[self._dp_mode] = mode

        await self._device.set_dps(status)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.set_dp(True, self._dp_id)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.set_dp(False, self._dp_id)

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

        # Update modes states
        if not self._state:
            self._attr_current_operation = OFF_MODE
        elif self._dp_mode is not None:
            for mode_value, mode_name in self._available_modes.items():
                if str(self.dp_value(CONF_MODE_DP)) == str(mode_value):
                    self._attr_current_operation = mode_name

        if (
            target_high := self.dp_value(CONF_TARGET_TEMPERATURE_HIGH_DP)
        ) or target_high is not None:
            self._attr_target_temperature_high = target_high

        if (
            target_low := self.dp_value(CONF_TARGET_TEMPERATURE_LOW_DP)
        ) or target_low is not None:
            self._attr_target_temperature_low = target_low


async_setup_entry = partial(
    async_setup_entry, DOMAIN, LocalTuyaWaterHeater, flow_schema
)
