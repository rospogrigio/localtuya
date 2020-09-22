"""
Platform to locally control Tuya-based cover devices.

It is recommend to setup LocalTUya using the graphical configuration flow:
Configuration-->Integrations-->+-->LocalTuya

YAML may be used as an alternative setup method.

Sample config yaml:

cover:
- platform: localtuya #REQUIRED
  host: 192.168.0.123 #REQUIRED
  local_key: 1234567891234567 #REQUIRED
  device_id: 123456789123456789abcd #REQUIRED
  friendly_name: Cover guests #REQUIRED
  protocol_version: 3.3 #REQUIRED
  name: cover_guests #OPTIONAL
  open_cmd: open #OPTIONAL, default is 'on'
  close_cmd: close #OPTIONAL, default is 'off'
  stop_cmd: stop #OPTIONAL, default is 'stop'
  get_position: 3 #OPTIONAL, default is 0
  set_position: 2 #OPTIONAL, default is 0
  last_movement: 7 #OPTIONAL, default is 0
  id: 1 #OPTIONAL
  icon: mdi:blinds #OPTIONAL
"""
import logging
from time import time, sleep

import voluptuous as vol

from homeassistant.components.cover import (
    CoverEntity,
    DOMAIN,
    PLATFORM_SCHEMA,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
    ATTR_POSITION
)
from homeassistant.const import (
    CONF_ID,
    CONF_FRIENDLY_NAME,
)
import homeassistant.helpers.config_validation as cv

from . import (
    BASE_PLATFORM_SCHEMA,
    TuyaDevice,
    LocalTuyaEntity,
    prepare_setup_entities,
    import_from_yaml,
)
from .const import (
    CONF_OPEN_CMD,
    CONF_CLOSE_CMD,
    CONF_STOP_CMD,
    CONF_GET_POSITION,
    CONF_SET_POSITION,
    CONF_LAST_MOVEMENT
)

from .pytuya import TuyaDevice

_LOGGER = logging.getLogger(__name__)

DEFAULT_OPEN_CMD = "open"
DEFAULT_CLOSE_CMD = "close"
DEFAULT_STOP_CMD = "stop"
DEFAULT_SET_POSITION = 0
DEFAULT_GET_POSITION = 0
DEFAULT_LAST_MOVEMENT = 0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA).extend(
    {
        vol.Optional(CONF_OPEN_CMD, default=DEFAULT_OPEN_CMD): cv.string,
        vol.Optional(CONF_CLOSE_CMD, default=DEFAULT_CLOSE_CMD): cv.string,
        vol.Optional(CONF_STOP_CMD, default=DEFAULT_STOP_CMD): cv.string,
        vol.Optional(CONF_SET_POSITION, default=DEFAULT_SET_POSITION): cv.positive_int,
        vol.Optional(CONF_GET_POSITION, default=DEFAULT_GET_POSITION): cv.positive_int,
        vol.Optional(CONF_LAST_MOVEMENT, default=DEFAULT_LAST_MOVEMENT): cv.positive_int,
    }
)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
            vol.Optional(CONF_OPEN_CMD, default=DEFAULT_OPEN_CMD): str,
            vol.Optional(CONF_CLOSE_CMD, default=DEFAULT_CLOSE_CMD): str,
            vol.Optional(CONF_STOP_CMD, default=DEFAULT_STOP_CMD): str,
            vol.Optional(CONF_SET_POSITION, default=DEFAULT_SET_POSITION): cv.positive_int,
            vol.Optional(CONF_GET_POSITION, default=DEFAULT_GET_POSITION): cv.positive_int,
            vol.Optional(CONF_LAST_MOVEMENT, default=DEFAULT_LAST_MOVEMENT): cv.positive_int,    
        }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya cover based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(
        config_entry, DOMAIN
    )
    if not entities_to_setup:
        return

    covers = []
    for device_config in entities_to_setup:
        covers.append(
            LocaltuyaCover(
                TuyaDevice(tuyainterface, config_entry.data[CONF_FRIENDLY_NAME]),
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(covers, True)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya cover."""
    return import_from_yaml(hass, config, DOMAIN)

class LocaltuyaCover(LocalTuyaEntity, CoverEntity):
    """Tuya cover devices."""

    def __init__(
        self,
        device,
        config_entry,
        coverid,
        **kwargs,
    ):
        super().__init__(device, config_entry, coverid, **kwargs)
        self._position = None
        self._current_cover_position = None
        self._last_movement = None
        self._last_position_set = None
        self._last_command = None
        print(
            "Initialized tuya cover  [{}] with switch status [{}]".format(
                self.name, self._status
            )
        )

    @property
    def is_closed(self):
        """Check if the cover is fully closed."""
        return self._current_cover_position == 100

    def status_updated(self):
        """Device status was updated."""
        self._last_movement = self.dps(str(self._config.get(CONF_LAST_MOVEMENT)))
        self._last_position = self.dps(str(self._config.get(CONF_SET_POSITION)))
        self._current_cover_position = self.dps(str(self._config.get(CONF_GET_POSITION)))
        self._last_command = self.dps(str(self._dps_id))

    @property
    def current_cover_position(self):
        """Return position of Tuya cover."""
        return self._current_cover_position 

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION     
        #TODO set supported features dynamically based on config or yaml input

    def set_cover_position(self, **kwargs):
        """Set the cover to a specific position from 0-100"""
        if ATTR_POSITION in kwargs:
            converted_position = int(kwargs[ATTR_POSITION])
            if converted_position in range(0,101):
                self._device.set_dps(converted_position, self._config[CONF_SET_POSITION])
            else:

    def open_cover(self, **kwargs):
        """Open the cover."""
        self._device.set_dps(self._config[CONF_OPEN_CMD], self._dps_id)

    def close_cover(self, **kwargs):
        """Close cover."""
        self._device.set_dps(self._config[CONF_CLOSE_CMD], self._dps_id)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self._device.set_dps(self._config[CONF_STOP_CMD], self._dps_id)