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
import requests

import voluptuous as vol

from homeassistant.components.fan import (SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH,
                                          FanEntity, SUPPORT_SET_SPEED,
                                          SUPPORT_OSCILLATE, SUPPORT_DIRECTION, PLATFORM_SCHEMA)

from homeassistant.const import STATE_OFF
"""from . import DATA_TUYA, TuyaDevice"""
from homeassistant.const import (CONF_HOST, CONF_ID, CONF_FRIENDLY_NAME, CONF_ICON, CONF_NAME)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'localtuyafan'

REQUIREMENTS = ['pytuya==7.0.9']

CONF_DEVICE_ID = 'device_id'
CONF_LOCAL_KEY = 'local_key'
CONF_PROTOCOL_VERSION = 'protocol_version'

DEFAULT_ID = '1'
DEFAULT_PROTOCOL_VERSION = 3.3


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION): vol.Coerce(float),
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up of the Tuya switch."""
    from . import pytuya
    fans = []
    localtuyadevice = pytuya.FanDevice(config.get(CONF_DEVICE_ID), config.get(CONF_HOST), config.get(CONF_LOCAL_KEY))
    localtuyadevice.set_version(float(config.get(CONF_PROTOCOL_VERSION)))
    _LOGGER.debug("localtuya fan: setup_platform: %s", localtuyadevice)

    fan_device = localtuyadevice
    fans.append(
            TuyaDevice(
                fan_device,
                config.get(CONF_NAME),
                config.get(CONF_FRIENDLY_NAME),
                config.get(CONF_ICON),
                config.get(CONF_ID),
            )
	)
    _LOGGER.info("Setup localtuya fan %s with device ID %s ", config.get(CONF_FRIENDLY_NAME), config.get(CONF_DEVICE_ID) )

    add_entities(fans, True)

class TuyaDevice(FanEntity):
    """A demonstration fan component."""

    # def __init__(self, hass, name: str, supported_features: int) -> None:
    def __init__(self, device, name, friendly_name, icon, switchid):
        """Initialize the entity."""
        self._device = device
        self._name = friendly_name
        self._available = True
        self._friendly_name = friendly_name
        self._icon = icon
        self._switch_id = switchid
        self._state = False
        self._supported_features = SUPPORT_SET_SPEED | SUPPORT_OSCILLATE
        self._speed = STATE_OFF
        self._oscillating = False

    @property
    def oscillating(self):
        """Return current oscillating status."""
        #if self._speed == STATE_OFF:
        #    return False
        _LOGGER.debug("localtuya fan: oscillating = %s", self._oscillating)
        return self._oscillating

    @property
    def name(self) -> str:
        """Get entity name."""
        return self._name

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._speed

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return [STATE_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]
        # return ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

    def turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity."""
        _LOGGER.debug("localtuya fan: turn_on speed to: %s", speed)
        # if speed is None:
        #    speed = SPEED_MEDIUM
        # self.set_speed(speed)
        self._device.turn_on()
        if speed is not None:
            self.set_speed(speed)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        _LOGGER.debug("localtuya fan: turn_off")
        self._device.set_status(False, '1')
        self._state = False
        self.schedule_update_ha_state()

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        _LOGGER.debug("localtuya fan: set_speed to: %s", speed)
        self._speed = speed
        # self.schedule_update_ha_state()
        if speed == STATE_OFF:
            self._device.set_status(False, '1')
            self._state = False
        elif speed == SPEED_LOW:
            self._device.set_value('2', '1')
        elif speed == SPEED_MEDIUM:
            self._device.set_value('2', '2')
        elif speed == SPEED_HIGH:
            self._device.set_value('2', '3')
        self.schedule_update_ha_state()

    # def set_direction(self, direction: str) -> None:
    #    """Set the direction of the fan."""
    #    self.direction = direction
    #    self.schedule_update_ha_state()

    def oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._oscillating = oscillating
        self._device.set_value('8', oscillating)
        self.schedule_update_ha_state()

    # @property
    # def current_direction(self) -> str:
    #    """Fan direction."""
    #    return self.direction

    @property
    def unique_id(self):
        """Return unique device identifier."""
        _LOGGER.debug("localtuya fan unique_id = %s", self._device)
        return self._device.id

    @property
    def available(self):
        """Return if device is available or not."""
        return self._available

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    def update(self):
        """Get state of Tuya switch."""
        success = False
        for i in range(3):
            if success is False:
                try:
                    status = self._device.status()
                    _LOGGER.debug("localtuya fan: status = %s", status)
                    self._state = status['dps']['1']
                    if status['dps']['1'] == False:
                        self._speed = STATE_OFF
                    elif int(status['dps']['2']) == 1:
                        self._speed = SPEED_LOW
                    elif int(status['dps']['2']) == 2:
                        self._speed = SPEED_MEDIUM
                    elif int(status['dps']['2']) == 3:
                        self._speed = SPEED_HIGH
                    # self._speed = status['dps']['2']
                    self._oscillating = status['dps']['8']
                    success = True
                except ConnectionError:
                    if i+1 == 3:
                        success = False
                        raise ConnectionError("Failed to update status.")
        self._available = success
