"""
Simple platform to control LOCALLY Tuya switch devices.

Sample config yaml

light:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    name: tuya_01
    friendly_name: This Light
    protocol_version: 3.3
"""
import socket
import logging
from time import time, sleep
from threading import Lock

from homeassistant.const import (
    CONF_ID,
    CONF_FRIENDLY_NAME,
)
from homeassistant.components.light import (
    LightEntity,
    DOMAIN,
    PLATFORM_SCHEMA,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
)
from homeassistant.util import color as colorutil

from . import BASE_PLATFORM_SCHEMA, import_from_yaml, prepare_setup_entities
from .pytuya import TuyaDevice

_LOGGER = logging.getLogger(__name__)

MIN_MIRED = 153
MAX_MIRED = 370
UPDATE_RETRY_LIMIT = 3

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya switch based on a config entry."""
    device, entities_to_setup = prepare_setup_entities(
        config_entry, DOMAIN
    )
    if not entities_to_setup:
        return

    lights = []
    for device_config in entities_to_setup:
        # this has to be done in case the device type is type_0d
        device.add_dps_to_request(device_config[CONF_ID])

        lights.append(
            LocaltuyaLight(
                TuyaCache(device, config_entry.data[CONF_FRIENDLY_NAME]),
                device_config[CONF_FRIENDLY_NAME],
                device_config[CONF_ID],
            )
        )

    async_add_entities(lights, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    return import_from_yaml(hass, config, DOMAIN)


class TuyaCache:
    """Cache wrapper for pytuya.TuyaDevices"""

    def __init__(self, device, friendly_name):
        """Initialize the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        self._device = device
        self._friendly_name = friendly_name
        self._lock = Lock()

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return self._device.id

    def __get_status(self, switchid):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.status()["dps"][switchid]
            except (ConnectionError, socket.timeout):
                pass
        _LOGGER.warning("Failed to get status after %d tries", UPDATE_RETRY_LIMIT)

    def set_dps(self, state, dps_index):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_dps(state, dps_index)
            except ConnectionError:
                pass
            except socket.timeout:
                pass
        _LOGGER.warning("Failed to set status after %d tries", UPDATE_RETRY_LIMIT)

    def status(self, switchid):
        """Get state of Tuya switch and cache the results."""
        with self._lock:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 15:
                sleep(0.5)
                self._cached_status = self.__get_status(switchid)
                self._cached_status_time = time()
            return self._cached_status

    def cached_status(self):
        return self._cached_status

   def state(self):
        self._device.state();
 
class LocaltuyaLight(LightEntity):
    """Representation of a Tuya switch."""
    DPS_INDEX_ON         = '1'
    DPS_INDEX_MODE       = '2'
    DPS_INDEX_BRIGHTNESS = '3'
    DPS_INDEX_COLOURTEMP = '4'
    DPS_INDEX_COLOUR     = '5'

    def __init__(self, device, friendly_name, bulbid):
        """Initialize the Tuya switch."""
        self._device = device
        self._available = False
        self._name = friendly_name
        self._state = False
        self._brightness = 127
        self._color_temp = 127
        self._bulb_id = bulbid

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                ("LocalTuya", f"local_{self._device.unique_id}")
            },
            "name": self._device._friendly_name,
            "manufacturer": "Tuya generic",
            "model": "SmartLight",
            "sw_version": "3.3",
        }

    def state(self):
        self._device.state()

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"local_{self._device.unique_id}"

    @property
    def available(self):
        """Return if device is available or not."""
        return self._available

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    def update(self):
        """Get state of Tuya switch."""
        try:
            self._update_state()
        except:
            self._available = False
        else:
            self._available = True

    def _update_state(self):
        status = self._device.status(self._bulb_id)
        self._state = status
        try:
            brightness = int(self._device.brightness())
            if brightness > 254:
                brightness = 255
            if brightness < 25:
                brightness = 25
            self._brightness = brightness
        except TypeError:
            pass
        self._color_temp = self._device.color_temp()

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

    #    @property
    #    def hs_color(self):
    #        """Return the hs_color of the light."""
    #        return (self._device.color_hsv()[0],self._device.color_hsv()[1])

    @property
    def color_temp(self):
        """Return the color_temp of the light."""
        try:
            return int(MAX_MIRED - (((MAX_MIRED - MIN_MIRED) / 255) * self._color_temp))
        except TypeError:
            pass

    @property
    def min_mireds(self):
        """Return color temperature min mireds."""
        return MIN_MIRED

    @property
    def max_mireds(self):
        """Return color temperature max mireds."""
        return MAX_MIRED

    def turn_on(self, **kwargs):
        """Turn on or control the light."""
        _LOGGER.debug("Turning on, state: %s", self._device.cached_status())
        if  not self._device.cached_status():
            self._device.set_dps(True, self._bulb_id)
        if ATTR_BRIGHTNESS in kwargs:
            converted_brightness = int(kwargs[ATTR_BRIGHTNESS])
            if converted_brightness <= 25:
                converted_brightness = 25
            self.set_brightness(converted_brightness)
        if ATTR_HS_COLOR in kwargs:
            raise ValueError(" TODO implement RGB from HS")
        if ATTR_COLOR_TEMP in kwargs:
            color_temp = int(
                255
                - (255 / (MAX_MIRED - MIN_MIRED))
                * (int(kwargs[ATTR_COLOR_TEMP]) - MIN_MIRED)
            )
            self._device.set_color_temp(color_temp)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        self._device.set_dps(False, self._bulb_id)

    @property
    def supported_features(self):
        """Flag supported features."""
        supports = SUPPORT_BRIGHTNESS
        if self._device.color_temp() != "999":
            supports = supports | SUPPORT_COLOR
        # supports = supports | SUPPORT_COLOR_TEMP
        return supports

    def support_color(self):
        return supported_features() & SUPPORT_COLOR

    def support_color_temp(self):
        return supported_features() & SUPPORT_COLOR_TEMP

    def color_temp(self):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._state[self.DPS][self.DPS_INDEX_COLOURTEMP]
            except ConnectionError:
                pass
            except KeyError:
                return "999"
            except socket.timeout:
                pass
        log.warn(
            "Failed to get color temp after {} tries".format(UPDATE_RETRY_LIMIT))

    def set_color_temp(self, color_temp):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                if not 0 <= colourtemp <= 255:
                    raise ValueError("The colour temperature needs to be between 0 and 255.")

                self._device.set_dps(colourtemp, self.DPS_INDEX_COLOURTEMP)
            except ConnectionError:
                pass
            except KeyError:
                pass
            except socket.timeout:
                pass
        log.warn(
            "Failed to set color temp after {} tries".format(UPDATE_RETRY_LIMIT))

    def set_brightness(self, brightness):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                if not 25 <= brightness <= 255:
                    raise ValueError("The brightness needs to be between 25 and 255.")

                self._device.set_dps(brightness, self.DPS_INDEX_BRIGHTNESS)
            except ConnectionError:
                pass
            except KeyError:
                pass
            except socket.timeout:
                pass
        log.warn(
            "Failed to set brightness after {} tries".format(UPDATE_RETRY_LIMIT))


    @staticmethod
    def _hexvalue_to_rgb(hexvalue):
        """
        Converts the hexvalue used by tuya for colour representation into
        an RGB value.
        
        Args:
            hexvalue(string): The hex representation generated by TuyaDevice._rgb_to_hexvalue()
        """
        r = int(hexvalue[0:2], 16)
        g = int(hexvalue[2:4], 16)
        b = int(hexvalue[4:6], 16)

        return (r, g, b)

    @staticmethod
    def _hexvalue_to_hsv(hexvalue):
        """
        Converts the hexvalue used by tuya for colour representation into
        an HSV value.
        
        Args:
            hexvalue(string): The hex representation generated by TuyaDevice._rgb_to_hexvalue()
        """
        h = int(hexvalue[7:10], 16) / 360
        s = int(hexvalue[10:12], 16) / 255
        v = int(hexvalue[12:14], 16) / 255

        return (h, s, v)

