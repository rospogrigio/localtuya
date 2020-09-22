"""
Simple platform to control LOCALLY Tuya light devices.

Sample config yaml

light:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    friendly_name: This Light
    protocol_version: 3.3
"""
import socket
import logging
from time import time, sleep

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
)

from . import (
    BASE_PLATFORM_SCHEMA,
    TuyaDevice,
    LocalTuyaEntity,
    import_from_yaml,
    prepare_setup_entities,
)

_LOGGER = logging.getLogger(__name__)

MIN_MIRED = 153
MAX_MIRED = 370
UPDATE_RETRY_LIMIT = 3

DPS_INDEX_ON = "1"
DPS_INDEX_MODE = "2"
DPS_INDEX_BRIGHTNESS = "3"
DPS_INDEX_COLOURTEMP = "4"
DPS_INDEX_COLOUR = "5"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up a Tuya light based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(config_entry, DOMAIN)
    if not entities_to_setup:
        return

    lights = []
    for device_config in entities_to_setup:
        # this has to be done in case the device type is type_0d
        tuyainterface.add_dps_to_request(device_config[CONF_ID])

        lights.append(
            LocaltuyaLight(
                TuyaCache(tuyainterface, config_entry.data[CONF_FRIENDLY_NAME]),
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(lights, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya light."""
    return import_from_yaml(hass, config, DOMAIN)



class LocaltuyaLight(LocalTuyaEntity, LightEntity):
    """Representation of a Tuya light."""

    def __init__(
        self,
        device,
        config_entry,
        lightid,
        **kwargs,
    ):
        """Initialize the Tuya light."""
        super().__init__(device, config_entry, lightid, **kwargs)
        self._state = False
        self._brightness = 127
        self._color_temp = 127

    @property
    def is_on(self):
        """Check if Tuya light is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

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

    @property
    def supported_features(self):
        """Flag supported features."""
        supports = SUPPORT_BRIGHTNESS
        if self._color_temp is not None:
            supports = supports | SUPPORT_COLOR
        return supports

    def turn_on(self, **kwargs):
        """Turn on or control the light."""
        self._device.set_dps(True, self._dps_id)

        if ATTR_BRIGHTNESS in kwargs:
            self._device.set_dps(
                max(int(kwargs[ATTR_BRIGHTNESS]), 25), DPS_INDEX_BRIGHTNESS
            )

        if ATTR_HS_COLOR in kwargs:
            raise ValueError(" TODO implement RGB from HS")

        if ATTR_COLOR_TEMP in kwargs:
            color_temp = int(
                255
                - (255 / (MAX_MIRED - MIN_MIRED))
                * (int(kwargs[ATTR_COLOR_TEMP]) - MIN_MIRED)
            )
            self._device.set_dps(color_temp, DPS_INDEX_COLOURTEMP)

    def turn_off(self, **kwargs):
        """Turn Tuya light off."""
        self._device.set_dps(False, self._dps_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dps_id)

        brightness = self.dps(DPS_INDEX_BRIGHTNESS)
        if brightness is not None:
            brightness = min(brightness, 255)
            brightness = max(brightness, 25)
        self._brightness = brightness

        self._color_temp = self.dps(DPS_INDEX_COLOURTEMP)
