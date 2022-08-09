"""Platform to locally control Tuya-based water heater devices."""
import asyncio
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.water_heater import (
    DOMAIN,
    STATE_ECO,
    STATE_ELECTRIC,
    STATE_GAS,
    STATE_HEAT_PUMP,
    STATE_HIGH_DEMAND,
    STATE_PERFORMANCE,
    WaterHeaterEntity,
    WaterHeaterEntityFeature
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,    
    CONF_TEMPERATURE_UNIT,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    TEMP_KELVIN,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_MODE_DP,
    CONF_MODE_ECO_VALUE,
    CONF_MODE_ELECTRIC_VALUE,
    CONF_MODE_GAS_VALUE,
    CONF_MODE_HEAT_PUMP_VALUE,
    CONF_MODE_HIGH_DEMAND_VALUE,
    CONF_MODE_PERFORMANCE_VALUE,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_PRECISION,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = PRECISION_WHOLE

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_TARGET_TEMPERATURE_DP): vol.In(dps),
        vol.Optional(CONF_MODE_DP): vol.In(dps),
        vol.Optional(CONF_MODE_ECO_VALUE): str,
        vol.Optional(CONF_MODE_ELECTRIC_VALUE): str,
        vol.Optional(CONF_MODE_GAS_VALUE): str,
        vol.Optional(CONF_MODE_HEAT_PUMP_VALUE): str,
        vol.Optional(CONF_MODE_HIGH_DEMAND_VALUE): str,
        vol.Optional(CONF_MODE_PERFORMANCE_VALUE): str,
        vol.Optional(CONF_TEMPERATURE_UNIT): vol.In(
            [TEMP_CELSIUS, TEMP_FAHRENHEIT, TEMP_KELVIN]
        ),
        vol.Optional(CONF_PRECISION): vol.In(
            [PRECISION_WHOLE, PRECISION_HALVES, PRECISION_TENTHS]
        ),
    }

class LocalTuyaWaterHeater(LocalTuyaEntity, WaterHeaterEntity):
    """Tuya water heater device."""

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocalTuyaWaterHeater."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._attr_temperature_unit = self._config.get(CONF_TEMPERATURE_UNIT)
        self._precision = self._config.get(CONF_PRECISION, DEFAULT_PRECISION)
        self._conf_attr_current_temperature_dp = self._config.get(CONF_CURRENT_TEMPERATURE_DP)
        self._conf_attr_target_temperature_dp = self._config.get(CONF_TARGET_TEMPERATURE_DP)
        self._conf_mode_dp = self._config.get(CONF_MODE_DP)
        self.TUYA_STATE_TO_HA = {}
        if (self._config.get(CONF_MODE_ECO_VALUE) is not None):
            self.TUYA_STATE_TO_HA[self._config.get(CONF_MODE_ECO_VALUE)] = STATE_ECO
        if (self._config.get(CONF_MODE_ELECTRIC_VALUE) is not None):
            self.TUYA_STATE_TO_HA[self._config.get(CONF_MODE_ELECTRIC_VALUE)] = STATE_ELECTRIC
        if (self._config.get(CONF_MODE_GAS_VALUE) is not None):
            self.TUYA_STATE_TO_HA[self._config.get(CONF_MODE_GAS_VALUE)] = STATE_GAS
        if (self._config.get(CONF_MODE_HEAT_PUMP_VALUE) is not None):
            self.TUYA_STATE_TO_HA[self._config.get(CONF_MODE_HEAT_PUMP_VALUE)] = STATE_HEAT_PUMP
        if (self._config.get(CONF_MODE_HIGH_DEMAND_VALUE) is not None):
            self.TUYA_STATE_TO_HA[self._config.get(CONF_MODE_HIGH_DEMAND_VALUE)] = STATE_HIGH_DEMAND
        if (self._config.get(CONF_MODE_PERFORMANCE_VALUE) is not None):
            self.TUYA_STATE_TO_HA[self._config.get(CONF_MODE_PERFORMANCE_VALUE)] = STATE_PERFORMANCE
        self.TUYA_STATE_TO_HA[STATE_OFF] = STATE_OFF
        self.HA_STATE_TO_TUYA = {}
        self.HA_STATE_TO_TUYA = {value: key for key, value in self.TUYA_STATE_TO_HA.items()}
        self._attr_operation_list = list(self.TUYA_STATE_TO_HA.values())
        _LOGGER.debug("Initialized water heater [%s]", self.name)

    """Reference for properties and methods:
       https://developers.home-assistant.io/docs/core/entity/water-heater
       Property methods that already work haven't been duplicated:
       https://github.com/home-assistant/core/blob/dev/homeassistant/components/water_heater/__init__.py
    """

    @property
    def supported_features(self):
        """Flag supported features. Only OPERATION_MODE is supported at the moment.
           TARGET_TEMPERATURE has been disabled based on safety guidance
           from Aquatech Heat Pumps for the Hydrotherm DYNAMIC/X8.
        """
        return WaterHeaterEntityFeature.OPERATION_MODE

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:water-boiler"

    async def async_set_operation_mode(self, operation_mode):
        """Set operation mode."""
        op_mode_tuya = self.HA_STATE_TO_TUYA.get(operation_mode)
        if op_mode_tuya is not None:
            if operation_mode == STATE_OFF:
                if self._attr_current_operation != STATE_OFF:
                    _LOGGER.debug("Switching off device.")
                    await self._device.set_dp(False, self._dp_id)
                else:
                    _LOGGER.debug("Ignoring request to switch off device that's already switched off. Doing nothing.")
            else:
                if self._attr_current_operation == STATE_OFF:
                    _LOGGER.debug("Switching on device.")
                    await self._device.set_dp(True, self._dp_id)
                if operation_mode != self._attr_current_operation:
                    _LOGGER.debug("Changing operation mode. Tuya: [%s]. HA: [%s]", (op_mode_tuya, operation_mode))
                    await self._device.set_dp(op_mode_tuya, self._conf_mode_dp)
        else:
            _LOGGER.error("Invalid operation mode. Tuya: [%s]. HA: [%s].", (op_mode_tuya, operation_mode))

    def status_updated(self):
        """Device status was updated."""
        if not self.has_config(CONF_CURRENT_TEMPERATURE_DP):
            _LOGGER.error("CONF_CURRENT_TEMPERATURE_DP is not set.")
            self._attr_current_temperature = None
        elif self.dps_conf(CONF_CURRENT_TEMPERATURE_DP) is None:
            _LOGGER.error("CONF_CURRENT_TEMPERATURE_DP value is invalid [None].")
            self._attr_current_temperature = None
        else:
            _LOGGER.debug("Device status updated. Raw current temperature value: [%s]", self.dps_conf(CONF_CURRENT_TEMPERATURE_DP))
            self._attr_current_temperature = self.dps_conf(CONF_CURRENT_TEMPERATURE_DP) * self._precision

        if not self.has_config(CONF_TARGET_TEMPERATURE_DP):
            _LOGGER.error("CONF_TARGET_TEMPERATURE_DP is not set.")
            self._attr_target_temperature = None
        elif self.dps_conf(CONF_TARGET_TEMPERATURE_DP) is None:
            _LOGGER.error("CONF_TARGET_TEMPERATURE_DP value is invalid [None].")
            self._attr_target_temperature = None
        else:
            _LOGGER.debug("Device status updated. Raw target temperature value: [%s]", self.dps_conf(CONF_TARGET_TEMPERATURE_DP))
            self._attr_target_temperature = self.dps_conf(CONF_TARGET_TEMPERATURE_DP) * self._precision

        if self.dps(self._dp_id):
            if not self.has_config(CONF_MODE_DP):
                _LOGGER.error("CONF_MODE_DP is not set. Returning STATE_OFF as a default state.")
                self._attr_current_operation = STATE_OFF
            elif self.dps_conf(CONF_MODE_DP) is None:
                _LOGGER.error("No value available for CONF_MODE_DP. Returning STATE_OFF as a default state.")
                self._attr_current_operation = STATE_OFF
            else:
                _LOGGER.debug("Device status updated. Tuya: [%s]. HA: [%s]", (self.dps_conf(CONF_MODE_DP), self.TUYA_STATE_TO_HA[self.dps_conf(CONF_MODE_DP)]))
                self._attr_current_operation = self.TUYA_STATE_TO_HA[self.dps_conf(CONF_MODE_DP)]
        else:
            _LOGGER.debug("Device was switched off. Device status updated.")
            self._attr_current_operation = STATE_OFF

async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaWaterHeater, flow_schema)
