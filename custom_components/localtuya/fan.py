"""Platform to locally control Tuya-based fan devices."""
import logging
from functools import partial

import voluptuous as vol

from homeassistant.components.fan import (
    FanEntity,
    DOMAIN,
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    SUPPORT_SET_SPEED,
    SUPPORT_OSCILLATE,
)

from .const import (
    CONF_FAN_SPEED_CONTROL,
    CONF_FAN_OSCILLATING_CONTROL,
    SPEED_AUTO,
)


from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_FAN_SPEED_CONTROL): vol.In(dps),
        vol.Optional(CONF_FAN_OSCILLATING_CONTROL): vol.In(dps),
        vol.Optional(SPEED_LOW, default=SPEED_LOW): vol.In([SPEED_LOW, "1", "2"]),
        vol.Optional(SPEED_MEDIUM, default=SPEED_MEDIUM): vol.In(
            [SPEED_MEDIUM, "mid", "2", "3"]
        ),
        vol.Optional(SPEED_HIGH, default=SPEED_HIGH): vol.In(
            [SPEED_HIGH, "auto", "3", "4"]
        ),
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
        super().__init__(device, config_entry, fanid, **kwargs)
        self._is_on = False
        self._speed = None
        self._oscillating = None

    @property
    def oscillating(self):
        """Return current oscillating status."""
        return self._oscillating

    @property
    def is_on(self):
        """Check if Tuya fan is on."""
        return self._is_on

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._speed

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity."""
        await self._device.set_dps(True, "1")
        if speed is not None:
            await self.async_set_speed(speed)
        else:
            self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        await self._device.set_dps(False, "1")
        self.schedule_update_ha_state()

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        dps_id = "%s" % self._dps_id

        self._speed = speed

        if speed == SPEED_OFF:
            await self._device.set_dps(False, "1")
        else:
            await self._device.set_dps(
                self._config.get(speed), self._config.get(CONF_FAN_SPEED_CONTROL)
            )

        self.schedule_update_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        await self._device.set_dps(oscillating, self._config.get(CONF_FAN_OSCILLATING_CONTROL))
        self.schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            return SUPPORT_SET_SPEED | SUPPORT_OSCILLATE
        else:
            return SUPPORT_SET_SPEED

    def status_updated(self):
        """Get state of Tuya fan."""
        mappings = {
            self._config.get(SPEED_LOW): SPEED_LOW,
            self._config.get(SPEED_MEDIUM): SPEED_MEDIUM,
            self._config.get(SPEED_HIGH): SPEED_HIGH,
        }

        self._is_on = self.dps(self._dps_id)

        if self.has_config(CONF_FAN_SPEED_CONTROL) and self.dps_conf(
            CONF_FAN_SPEED_CONTROL
        ):
            try:
                self._speed = mappings[self.dps_conf(CONF_FAN_SPEED_CONTROL)]

            except KeyError:
                _LOGGER.warning(
                    "%s: Ignoring unknown fan controller state: %s",
                    self.name,
                    self.dps_conf(CONF_FAN_SPEED_CONTROL),
                )
                self._speed = None

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL) and self.dps_conf(
            CONF_FAN_OSCILLATING_CONTROL
        ):
            self._oscillating = self.dps_conf(CONF_FAN_OSCILLATING_CONTROL)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaFan, flow_schema)
