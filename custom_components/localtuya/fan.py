"""Platform to locally control Tuya-based fan devices."""
import logging
from functools import partial

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

from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
      vol.Optional(CONF_FAN_SPEED): vol.In(dps),
      vol.Optional(CONF_FAN_OSCILLATING): vol.In(dps),
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
        self._speed = SPEED_OFF
        self._oscillating = False
        self._type = 0

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

    def turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity."""
        self._device.set_dps(True, "1")
        if speed is not None:
            self.set_speed(speed)
        else:
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self._device.set_dps(False, "1")
        self.schedule_update_ha_state()

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        mappings = {
            SPEED_LOW: [1, "low"],
            SPEED_MEDIUM: [2, "medium"],
            SPEED_HIGH: [3, "high"],
            SPEED_AUTO: [2, "medium"],
        }

        dps_id = "%s" % self._dps_id

        self._speed = speed

        if speed == SPEED_OFF:
            self._device.set_dps(False, "1")
        else:
            self._device.set_dps(mappings[speed][self._type - 1], dps_id)

        self.schedule_update_ha_state()

    def oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._oscillating = oscillating
        self._device.set_value("8", oscillating)
        self.schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED | SUPPORT_OSCILLATE

    def status_updated(self):
        """Get state of Tuya fan."""
        mappings = {
            "1": [SPEED_LOW, 1],
            "2": [SPEED_MEDIUM, 1],
            "3": [SPEED_HIGH, 1],
            "4": [SPEED_HIGH, 1],
            "low": [SPEED_LOW, 2],
            "medium": [SPEED_MEDIUM, 2],
            "high": [SPEED_HIGH, 2],
            "auto": [SPEED_LOW, 2],
        }

        dps_id = "%s" % self._dps_id

        self._is_on = self.dps(self._dps_id)

        self._speed, self._type = mappings[self._status["dps"][dps_id]
        self._type = mappings[self._status["dps"][dps_id]][1]

        if self.has_config(FAN_OSCILLATING):
            self._oscillating = self._status["dps"][self.dps_conf(CONF_FAN_OSCILLATING)]


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaFan, flow_schema)
