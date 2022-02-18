"""Platform to locally control Tuya-based fan devices."""
import logging
import math
from functools import partial

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    DOMAIN,
    SUPPORT_DIRECTION,
    SUPPORT_OSCILLATE,
    SUPPORT_SET_SPEED,
    FanEntity,
)
from homeassistant.util.percentage import (
    int_states_in_range,
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_FAN_DIRECTION,
    CONF_FAN_DIRECTION_FWD,
    CONF_FAN_DIRECTION_REV,
    CONF_FAN_ORDERED_LIST,
    CONF_FAN_OSCILLATING_CONTROL,
    CONF_FAN_SPEED_CONTROL,
    CONF_FAN_SPEED_MAX,
    CONF_FAN_SPEED_MIN,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_FAN_SPEED_CONTROL): vol.In(dps),
        vol.Optional(CONF_FAN_OSCILLATING_CONTROL): vol.In(dps),
        vol.Optional(CONF_FAN_DIRECTION): vol.In(dps),
        vol.Optional(CONF_FAN_DIRECTION_FWD, default="forward"): cv.string,
        vol.Optional(CONF_FAN_DIRECTION_REV, default="reverse"): cv.string,
        vol.Optional(CONF_FAN_SPEED_MIN, default=1): cv.positive_int,
        vol.Optional(CONF_FAN_SPEED_MAX, default=9): cv.positive_int,
        vol.Optional(CONF_FAN_ORDERED_LIST, default="disabled"): cv.string,
    }


class LocaltuyaFan(LocalTuyaEntity, FanEntity):
    """Representation of a Tuya fan."""

    def __init__(
        self,
        device,
        config_entry,
        fanid,
        **kwargs,
    ):
        """Initialize the entity."""
        super().__init__(device, config_entry, fanid, _LOGGER, **kwargs)
        self._is_on = False
        self._oscillating = None
        self._direction = None
        self._percentage = None
        self._speed_range = (
            self._config.get(CONF_FAN_SPEED_MIN),
            self._config.get(CONF_FAN_SPEED_MAX),
        )
        self._ordered_list = self._config.get(CONF_FAN_ORDERED_LIST).split(",")
        self._ordered_list_mode = None

        if isinstance(self._ordered_list, list) and len(self._ordered_list) > 1:
            self._use_ordered_list = True
            _LOGGER.debug(
                "Fan _use_ordered_list: %s > %s",
                self._use_ordered_list,
                self._ordered_list,
            )
        else:
            self._use_ordered_list = False
            _LOGGER.debug("Fan _use_ordered_list: %s", self._use_ordered_list)

    @property
    def oscillating(self):
        """Return current oscillating status."""
        return self._oscillating

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        return self._direction

    @property
    def is_on(self):
        """Check if Tuya fan is on."""
        return self._is_on

    @property
    def percentage(self):
        """Return the current percentage."""
        return self._percentage

    async def async_turn_on(
        self,
        speed: str = None,
        percentage: int = None,
        preset_mode: str = None,
        **kwargs,
    ) -> None:
        """Turn on the entity."""
        _LOGGER.debug("Fan async_turn_on")
        await self._device.set_dp(True, self._dp_id)
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        _LOGGER.debug("Fan async_turn_off")

        await self._device.set_dp(False, self._dp_id)
        self.schedule_update_ha_state()

    async def async_set_percentage(self, percentage):
        """Set the speed of the fan."""
        _LOGGER.debug("Fan async_set_percentage: %s", percentage)

        if percentage is not None:
            if percentage == 0:
                return await self.async_turn_off()
            if not self.is_on:
                await self.async_turn_on()
            if self._use_ordered_list:
                await self._device.set_dp(
                    str(
                        percentage_to_ordered_list_item(self._ordered_list, percentage)
                    ),
                    self._config.get(CONF_FAN_SPEED_CONTROL),
                )
                _LOGGER.debug(
                    "Fan async_set_percentage: %s > %s",
                    percentage,
                    percentage_to_ordered_list_item(self._ordered_list, percentage),
                )

            else:
                await self._device.set_dp(
                    str(
                        math.ceil(
                            percentage_to_ranged_value(self._speed_range, percentage)
                        )
                    ),
                    self._config.get(CONF_FAN_SPEED_CONTROL),
                )
                _LOGGER.debug(
                    "Fan async_set_percentage: %s > %s",
                    percentage,
                    percentage_to_ranged_value(self._speed_range, percentage),
                )
            self.schedule_update_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        _LOGGER.debug("Fan async_oscillate: %s", oscillating)
        await self._device.set_dp(
            oscillating, self._config.get(CONF_FAN_OSCILLATING_CONTROL)
        )
        self.schedule_update_ha_state()

    async def async_set_direction(self, direction):
        """Set the direction of the fan."""
        _LOGGER.debug("Fan async_set_direction: %s", direction)

        if direction == DIRECTION_FORWARD:
            value = self._config.get(CONF_FAN_DIRECTION_FWD)

        if direction == DIRECTION_REVERSE:
            value = self._config.get(CONF_FAN_DIRECTION_REV)
        await self._device.set_dp(value, self._config.get(CONF_FAN_DIRECTION))
        self.schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        features = 0

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            features |= SUPPORT_OSCILLATE

        if self.has_config(CONF_FAN_SPEED_CONTROL):
            features |= SUPPORT_SET_SPEED

        if self.has_config(CONF_FAN_DIRECTION):
            features |= SUPPORT_DIRECTION

        return features

    @property
    def speed_count(self) -> int:
        """Speed count for the fan."""
        speed_count = int_states_in_range(self._speed_range)
        _LOGGER.debug("Fan speed_count: %s", speed_count)
        return speed_count

    def status_updated(self):
        """Get state of Tuya fan."""
        self._is_on = self.dps(self._dp_id)

        current_speed = self.dps_conf(CONF_FAN_SPEED_CONTROL)
        if self._use_ordered_list:
            _LOGGER.debug(
                "Fan current_speed ordered_list_item_to_percentage: %s from %s",
                current_speed,
                self._ordered_list,
            )
            if current_speed is not None:
                self._percentage = ordered_list_item_to_percentage(
                    self._ordered_list, current_speed
                )

        else:
            _LOGGER.debug(
                "Fan current_speed ranged_value_to_percentage: %s from %s",
                current_speed,
                self._speed_range,
            )
            if current_speed is not None:
                self._percentage = ranged_value_to_percentage(
                    self._speed_range, int(current_speed)
                )

        _LOGGER.debug("Fan current_percentage: %s", self._percentage)

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            self._oscillating = self.dps_conf(CONF_FAN_OSCILLATING_CONTROL)
            _LOGGER.debug("Fan current_oscillating : %s", self._oscillating)

        if self.has_config(CONF_FAN_DIRECTION):
            value = self.dps_conf(CONF_FAN_DIRECTION)
            if value is not None:
                if value == self._config.get(CONF_FAN_DIRECTION_FWD):
                    self._direction = DIRECTION_FORWARD

                if value == self._config.get(CONF_FAN_DIRECTION_REV):
                    self._direction = DIRECTION_REVERSE
            _LOGGER.debug("Fan current_direction : %s > %s", value, self._direction)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaFan, flow_schema)
