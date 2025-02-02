"""Platform to locally control Tuya-based button devices."""
import logging
from functools import partial
from .config_flow import _col_to_select

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.components.humidifier import (
    DOMAIN,
    HumidifierDeviceClass,
    DEVICE_CLASSES_SCHEMA,
    HumidifierEntity,
    HumidifierEntityDescription,
    HumidifierEntityFeature,
)
from homeassistant.components.humidifier.const import (
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
)

CONF_HUMIDIFIER_SET_HUMIDITY_DP = "humidifier_set_humidity_dp"
CONF_HUMIDIFIER_CURRENT_HUMIDITY_DP = "humidifier_current_humidity_dp"
CONF_HUMIDIFIER_MODE_DP = "humidifier_mode_dp"
CONF_HUMIDIFIER_AVAILABLE_MODES = "humidifier_available_modes"

from .common import LocalTuyaEntity, async_setup_entry


_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_HUMIDIFIER_SET_HUMIDITY_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_HUMIDIFIER_MODE_DP): _col_to_select(dps, is_dps=True),
        vol.Required(ATTR_MIN_HUMIDITY, default=DEFAULT_MIN_HUMIDITY): int,
        vol.Required(ATTR_MAX_HUMIDITY, default=DEFAULT_MAX_HUMIDITY): int,
        vol.Optional(CONF_HUMIDIFIER_AVAILABLE_MODES): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }


class LocaltuyaHumidifier(LocalTuyaEntity, HumidifierEntity):
    """Representation of a Localtuya Humidifier."""

    _available_modes = CONF_HUMIDIFIER_MODE_DP
    _dp_current_humidity = CONF_HUMIDIFIER_CURRENT_HUMIDITY_DP
    _dp_mode = CONF_HUMIDIFIER_MODE_DP
    _dp_set_humidity = CONF_HUMIDIFIER_SET_HUMIDITY_DP

    def __init__(
        self,
        device,
        config_entry,
        humidifierID,
        **kwargs,
    ):
        """Initialize the Tuya button."""
        super().__init__(device, config_entry, humidifierID, _LOGGER, **kwargs)
        self._state = None

        if self._config.get(self._dp_mode) and self._config.get(self._available_modes):
            self._attr_supported_features |= HumidifierEntityFeature.MODES

        self._attr_min_humidity = self._config.get(
            ATTR_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY
        )
        self._attr_max_humidity = self._config.get(
            ATTR_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY
        )

    @property
    def is_on(self) -> bool:
        """Return the device is on or off."""
        return self._state

    @property
    def mode(self) -> str | None:
        """Return the current mode."""
        return self.dp_value(self._dp_mode)

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""
        target_dp = self._config.get(self._dp_set_humidity, None)

        return self.dp_value(target_dp) if target_dp else None

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        curr_humidity = self._config.get(self._dp_current_humidity)

        return self.dp_value(self._dp_current_humidity) if curr_humidity else None

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self._device.set_dp(True, self._dp_id)

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self._device.set_dp(False, self._dp_id)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        set_humidity_dp = self._config.get(self._dp_set_humidity, None)
        if set_humidity_dp is None:
            return None

        await self._device.set_dp(humidity, set_humidity_dp)

    @property
    def available_modes(self):
        """Return the list of presets that this device supports."""
        if modes := self._config.get(self._available_modes, None):
            modes = [v.lstrip() for v in modes.strip(",")]

        return modes

    async def async_set_mode(self, mode):
        """Set new target preset mode."""
        set_mode_dp = self._config.get(self._dp_set_humidity, None)
        if set_mode_dp is None:
            return None

        await self._device.set_dp(set_mode_dp, mode)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaHumidifier, flow_schema)
