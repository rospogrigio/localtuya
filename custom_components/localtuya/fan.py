"""
Simple platform to control LOCALLY Tuya cover devices.

Sample config yaml

fan:
  - platform: localtuya
    host: 192.168.0.123
    local_key: 1234567891234567
    device_id: 123456789123456789abcd
    name: fan guests
    friendly_name: fan guests
    protocol_version: 3.3
    id: 1

"""
import logging
from time import time, sleep

from homeassistant.components.fan import (
    FanEntity,
    DOMAIN,
    PLATFORM_SCHEMA,
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    SUPPORT_SET_SPEED,
    SUPPORT_OSCILLATE,
)
from homeassistant.const import CONF_ID, CONF_FRIENDLY_NAME

from . import (
    BASE_PLATFORM_SCHEMA,
    TuyaDevice,
    LocalTuyaEntity,
    prepare_setup_entities,
    import_from_yaml,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya fan based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(config_entry, DOMAIN)
    if not entities_to_setup:
        return

    fans = []

    for device_config in entities_to_setup:
        fans.append(
            LocaltuyaFan(
                TuyaCache(tuyainterface, config_entry.data[CONF_FRIENDLY_NAME]),
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(fans, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya fan."""
    return import_from_yaml(hass, config, DOMAIN)



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
        self._speed = speed
        if speed == SPEED_OFF:
            self._device.set_dps(False, "1")
        elif speed == SPEED_LOW:
            self._device.set_dps("1", "2")
        elif speed == SPEED_MEDIUM:
            self._device.set_dps("2", "2")
        elif speed == SPEED_HIGH:
            self._device.set_dps("3", "2")
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
        self._is_on = self._status["dps"]["1"]
        if not self._status["dps"]["1"]:
            self._speed = SPEED_OFF
        elif self._status["dps"]["2"] == "1":
            self._speed = SPEED_LOW
        elif self._status["dps"]["2"] == "2":
            self._speed = SPEED_MEDIUM
        elif self._status["dps"]["2"] == "3":
            self._speed = SPEED_HIGH
        self._oscillating = self._status["dps"]["8"]
