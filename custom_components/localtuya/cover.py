"""
Simple platform to locally control Tuya-based cover devices.

Sample config yaml:

cover:
- platform: localtuya #REQUIRED
  host: 192.168.0.123 #REQUIRED
  local_key: 1234567891234567 #REQUIRED
  device_id: 123456789123456789abcd #REQUIRED
  name: cover_guests #REQUIRED
  friendly_name: Cover guests #REQUIRED
  protocol_version: 3.3 #REQUIRED
  get_position_key: 3 #REQUIRED, default is 0
  set_position_key: 2 #REQUIRED, default is 0
  last_movement_key: 7 #REQUIRED, default is 0
  cover_command_key: 1 #REQUIRED, default is 0
  id: 1 #OPTIONAL
  icon: mdi:blinds #OPTIONAL
  open_cmd: open #OPTIONAL, default is 'on'
  close_cmd: close #OPTIONAL, default is 'off'
  stop_cmd: stop #OPTIONAL, default is 'stop'
  get_position_key: 1 #OPTIONAL, default is 0

"""
import logging
from time import time, sleep
from threading import Lock

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
    CONF_COVERS,
    CONF_FRIENDLY_NAME,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv

from . import BASE_PLATFORM_SCHEMA, prepare_setup_entities, import_from_yaml
from .const import CONF_COVER_COMMAND_KEY, CONF_OPEN_CMD, CONF_CLOSE_CMD, CONF_STOP_CMD, CONF_GET_POSITION_KEY, CONF_SET_POSITION_KEY, CONF_LAST_MOVEMENT_KEY
from .pytuya import TuyaDevice

_LOGGER = logging.getLogger(__name__)

DEFAULT_OPEN_CMD = "on"
DEFAULT_CLOSE_CMD = "off"
DEFAULT_STOP_CMD = "stop"
DEFAULT_SET_POSITION_KEY = 0
DEFAULT_GET_POSITION_KEY = 0
DEFAULT_LAST_MOVEMENT_KEY = 0
DEFAULT_COVER_COMMAND_KEY = 0

MIN_POSITION = 0
MAX_POSITION = 100
UPDATE_RETRY_LIMIT = 3


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA).extend(
    {
        vol.Required(CONF_COVER_COMMAND_KEY, default=DEFAULT_COVER_COMMAND_KEY): cv.positive_int, # TODO only allow user to select from returned dps list
        vol.Optional(CONF_OPEN_CMD, default=DEFAULT_OPEN_CMD): cv.string,
        vol.Optional(CONF_CLOSE_CMD, default=DEFAULT_CLOSE_CMD): cv.string,
        vol.Optional(CONF_STOP_CMD, default=DEFAULT_STOP_CMD): cv.string,
        vol.Optional(CONF_SET_POSITION_KEY, default=DEFAULT_SET_POSITION_KEY): cv.positive_int, # TODO only allow user to select from returned dps list
        vol.Optional(CONF_GET_POSITION_KEY, default=DEFAULT_GET_POSITION_KEY): cv.positive_int, # TODO only allow user to select from returned dps list
        vol.Optional(CONF_LAST_MOVEMENT_KEY, default=DEFAULT_LAST_MOVEMENT_KEY): cv.positive_int, # TODO only allow user to select from returned dps list
    }
)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
            vol.Required(CONF_COVER_COMMAND_KEY, default=DEFAULT_COVER_COMMAND_KEY): cv.positive_int,
            vol.Optional(CONF_OPEN_CMD, default=DEFAULT_OPEN_CMD): str,
            vol.Optional(CONF_CLOSE_CMD, default=DEFAULT_CLOSE_CMD): str,
            vol.Optional(CONF_STOP_CMD, default=DEFAULT_STOP_CMD): str,
            vol.Optional(CONF_SET_POSITION_KEY, default=DEFAULT_SET_POSITION_KEY): cv.positive_int,
            vol.Optional(CONF_GET_POSITION_KEY, default=DEFAULT_GET_POSITION_KEY): cv.positive_int,
            vol.Optional(CONF_LAST_MOVEMENT_KEY, default=DEFAULT_LAST_MOVEMENT_KEY): cv.positive_int,    
        }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya cover based on a config entry."""
    device, entities_to_setup = prepare_setup_entities(
        config_entry, DOMAIN
    )
    if not entities_to_setup:
        return

    # TODO: keeping for now but should be removed
    dps = {}

    covers = []
    for device_config in entities_to_setup:
        dps[device_config[CONF_ID]] = None
        covers.append(
            LocaltuyaCover(
                TuyaCache(device),
                device_config[CONF_FRIENDLY_NAME],
                device_config[CONF_ID],
                device_config.get(CONF_COVER_COMMAND_KEY),
                device_config.get(CONF_OPEN_CMD),
                device_config.get(CONF_CLOSE_CMD),
                device_config.get(CONF_STOP_CMD),
                device_config.get(CONF_SET_POSITION_KEY),
                device_config.get(CONF_GET_POSITION_KEY),
                device_config.get(CONF_LAST_MOVEMENT_KEY),
            )
#    print('Setup localtuya cover [{}] with device ID [{}] '.format(config.get(CONF_FRIENDLY_NAME), config.get(CONF_ID)))
#    _LOGGER.info("Setup localtuya cover %s with device ID=%s", config.get(CONF_FRIENDLY_NAME), config.get(CONF_ID) )
#    _LOGGER.debug("Cover %s uses open_cmd=%s close_cmd=%s stop_cmd=%s", config.get(CONF_FRIENDLY_NAME), config.get(CONF_OPEN_CMD), config.get(CONF_CLOSE_CMD), config.get(CONF_STOP_CMD) )
        )

    device.set_dpsUsed(dps)
    async_add_entities(covers, True)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya cover."""
    return import_from_yaml(hass, config, DOMAIN)


class TuyaCache:
    """Cache wrapper for pytuya.TuyaDevice"""

    def __init__(self, device, friendly_name):
        """Initialize the cache."""
        self._cached_status = ""
        self._friendly_name = friendly_name
        self._cached_status_time = 0
        self._device = device
        self._lock = Lock()

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return self._device.id

    def __get_status(self):
        # _LOGGER.info("running def __get_status from cover")
        for i in range(5):
            try:
                status = self._device.status()
                return status
            except Exception:
                print(
                    "Failed to update status of device [{}]".format(
                        self._device.address
                    )
                )
                sleep(1.0)
                if i + 1 == 3:
                    _LOGGER.error(
                        "Failed to update status of device %s", self._device.address
                    )
                    #                    return None
                    raise ConnectionError("Failed to update status .")

    def set_dps(self, state, dps_index):
        #_LOGGER.info("running def set_dps from cover")
        """Change the Tuya cover status and clear the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        for i in range(5):
            try:
                #_LOGGER.info("Running a try from def set_dps from cover where state=%s and dps_index=%s", state, dps_index)
                return self._device.set_dps(state, dps_index)
            except Exception:
                print(
                    "Failed to set status of device [{}]".format(self._device.address)
                )
                if i + 1 == 3:
                    _LOGGER.error(
                        "Failed to set status of device %s", self._device.address
                    )
                    return

    #                    raise ConnectionError("Failed to set status.")

    def status(self):
        """Get state of Tuya cover and cache the results."""
        # _LOGGER.info("running def status(self) from cover")
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 15:
                sleep(0.5)
                self._cached_status = self.__get_status()
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()

class LocaltuyaCover(CoverEntity):
    """Tuya cover devices."""

    def __init__(self, device, friendly_name, coverid, cover_command_key, open_cmd, close_cmd, stop_cmd, set_position_key, get_position_key, last_movement_key):
        self._device = device
        self._available = False 
        self._name = friendly_name
        self._cover_id = coverid
        self._status = None
        self._state = None
        self._last_movement = None
        self._last_position_set = None
        self._last_command = None
        self._current_cover_position = 50
        self._cover_command_key = cover_command_key
        self._open_cmd = open_cmd
        self._close_cmd = close_cmd
        self._stop_cmd = stop_cmd
        self._get_position_key = get_position_key
        self._set_position_key = set_position_key
        self._last_movement_key = last_movement_key
        
        print(
            "Initialized tuya cover [{}] with cover status [{}] and state [{}]".format(
                self._name, self._status, self._state
            )
        )

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                ("LocalTuya", f"local_{self._device.unique_id}")
            },
            "name": self._device._friendly_name,
            "manufacturer": "Tuya generic",
            "model": "SmartCover",
            "sw_version": "3.3",
        }

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"local_{self._device.unique_id}_{self._cover_id}"

    @property
    def name(self):
        """Get name of Tuya cover."""
        return self._name
        
    @property
    def cover_command_key(self):
        """Get name of Tuya cover."""
        #_LOGGER.info("def cover_command_key called=%s", self._cover_command_key)
        return self._cover_command_key

    @property
    def open_cmd(self):
        """Get name of open command."""
        #_LOGGER.info("def open_cmd called=%s", self._open_cmd)
        return self._open_cmd

    @property
    def close_cmd(self):
        """Get name of close command."""
        #_LOGGER.info("def close_cmd called=%s", self._close_cmd)
        return self._close_cmd

    @property
    def stop_cmd(self):
        """Get name of stop command."""
        #_LOGGER.info("def close_cmd called=%s", self._stop_cmd)
        return self._stop_cmd

    @property
    def last_movement_key(self):
        """Get last movement key"""
        #_LOGGER.info("def last_movement_key called=%s", self._last_movement_key)
        return self._last_movement_key


    @property
    def last_movement(self):
        #_LOGGER.info("def last_movement called=%s", self._last_movement)
        """Return the last movement of the device (should be "Opening" or "Closing")"""
        return self._last_movement

    def last_position_set(self):
        #_LOGGER.info("def last_position_set called=%s", self._last_position_set)
        """Return the last position set of the device"""
        return self._last_position_set
        
    @property
    def last_command(self):
        #_LOGGER.info("def last_command called=%s", self._last_command)
        """Return the last command of the device"""
        return self._last_command

    @property
    def is_open(self):
        """Check if the cover is partially or fully open."""
        #_LOGGER.info("def is_open called, self._current_cover_position = %s", self._current_cover_position)
        if self._current_cover_position != 100:
            #_LOGGER.info("is_open returning true)")
            return True
        #_LOGGER.info("is_open returning false")
        return False

    @property
    def is_closed(self):
        """Check if the cover is fully closed."""
        #_LOGGER.info("def is_closed called")
        if self._current_cover_position == 100:
            #_LOGGER.info("is_closed returning true)")
            return True
        #_LOGGER.info("is_closed returning false")
        return False

    def update(self):
        """Update cover attributes and store in cache."""
        #_LOGGER.info("update(self) called")
        try:
            #_LOGGER.info("about to call status=self._device.status() from def update(self)")
            status = self._device.status()
            #_LOGGER.info("def update set status =%s", status)
            self._cached_status = status
            #_LOGGER.info("self._cached_status set =%s", self._cached_status)
            
            self._update_last_command()
            self._update_last_movement()
            self._update_last_position_set()
            self._update_current_cover_position()

        except:
            #_LOGGER.info("def update returned except, setting available to false")
            self._available = False
        else:
            #_LOGGER.info("def update reached else, setting available to true")
            self._available = True

    def _update_last_movement(self):
        #_LOGGER.info("_update_last_movement called, currently = %s and self._cached_status=%s ", self._last_movement, self._cached_status)
        
        self._last_movement = self._cached_status['dps'][str(self._last_movement_key)]
        #_LOGGER.info("_update_last_movement set, now = %s", self._last_movement)
        
    def _update_last_command(self):
        #_LOGGER.info("_update_last_command called, currently = %s and self._cached_status=%s", self._last_command, self._cached_status)
        self._last_command = self._cached_status['dps'][str(self._cover_command_key)]
        #_LOGGER.info("_update_last_command set, now = %s", self._last_command)

        
    def _update_last_position_set(self):
        #_LOGGER.info("_update_last_position_set called, currently = %s and self._cached_status=%s", self._last_position_set, self._cached_status)
        self._last_position_set = self._cached_status['dps'][str(self._set_position_key)]
        #_LOGGER.info("_update_last_position_set set, now = %s", self._last_position_set)
        
        
    def _update_current_cover_position(self):
        #_LOGGER.info("_update_current_cover_position called, currently = %s and self._cached_status=%s", self._current_cover_position, self._cached_status)
        self._current_cover_position = self._cached_status['dps'][str(self._get_position_key)]
        #_LOGGER.info("_update_current_cover_position set, now = %s", self._current_cover_position)

    @property
    def current_cover_position(self):
        #_LOGGER.info("current_cover_position called")
        """Return position of Tuya cover."""
        return self._current_cover_position 

    @property
    def min_position(self):
        """Return minimum position of Tuya cover."""
        return MIN_POSITION

    @property
    def max_position(self):
        """Return maximum position of Tuya cover."""
        return MAX_POSITION 

    @property
    def available(self):
        """Return if device is available or not."""
        return self._available

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION
        return supported_features

    @property
    def is_opening(self):
        #_LOGGER.info("is_opening called")
        last_movement = self._last_movement;
        if last_movement == 'Opening':
            return True
        return False

    @property
    def is_closing(self):
        #_LOGGER.info("is_closing called")
        last_movement = self._last_movement;
        if last_movement == 'Closing':
            return True
        return False

    def set_cover_position(self, **kwargs):
        """Set the cover to a specific position from 0-100"""
        #_LOGGER.debug("set_cover_position called")
        if ATTR_POSITION in kwargs:
            converted_position = int(kwargs[ATTR_POSITION])
            if converted_position in range(0,101):
                _LOGGER.info("set_cover_position about to set position to =%s", converted_position)
                self._device.set_dps(self._set_position_key, converted_position)
            else:
                _LOGGER.warning("set_position given number outside range")

    def open_cover(self, **kwargs):
        """Open the cover."""
        #_LOGGER.info("open_cover called where self._cover_command_key=%s and self._open_cmd=%s", self._cover_command_key, self._open_cmd)
        self._device.set_dps(str(self._cover_command_key), str(self._open_cmd))

    def close_cover(self, **kwargs):
        """Close the cover."""
        #_LOGGER.info("close_cover called where self._cover_command_key=%s and self._close_cmd=%s", self._cover_command_key, self._close_cmd)
        self._device.set_dps(str(self._cover_command_key), str(self._close_cmd))

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        #_LOGGER.info("stop_cover called where self._cover_command_key=%s and self._stop_cmd=%s", self._cover_command_key, self._stop_cmd)
        self._device.set_dps(str(self._cover_command_key), str(self.stop_cmd))
                
                