"""Platform to locally control Tuya-based light devices."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    DOMAIN,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP,
    SUPPORT_COLOR,
    LightEntity,
)
from homeassistant.const import CONF_BRIGHTNESS, CONF_COLOR_TEMP

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_BRIGHTNESS_LOWER, CONF_BRIGHTNESS_UPPER, CONF_COLOR_TEMP_LOWER, CONF_COLOR_TEMP_UPPER, CONF_HS_COLOR, CONF_LIGHT_MODE

_LOGGER = logging.getLogger(__name__)

MIN_MIRED = 153
MAX_MIRED = 500

DEFAULT_LOWER_COLOR_TEMP = 0
DEFAULT_UPPER_COLOR_TEMP = 1000

DEFAULT_LOWER_BRIGHTNESS = 29
DEFAULT_UPPER_BRIGHTNESS = 1000

LIGHT_MODES = ["white","colour","scene","music"]


def map_range(value, from_lower, from_upper, to_lower, to_upper):
    """Map a value in one range to another."""
    mapped = (value - from_lower) * (to_upper - to_lower) / (
        from_upper - from_lower
    ) + to_lower
    return round(min(max(mapped, to_lower), to_upper))

def map_range_inverted(value, from_lower, from_upper, to_lower, to_upper):
    """Map a value in one range to another (inverted)."""
    mapped = map_range(value, from_lower, from_upper, to_lower, to_upper)
    inverted = to_lower + (to_upper - mapped)
    return inverted

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_LIGHT_MODE): vol.In(dps),
        vol.Optional(CONF_BRIGHTNESS): vol.In(dps),
        vol.Optional(CONF_COLOR_TEMP): vol.In(dps),
        vol.Optional(CONF_HS_COLOR): vol.In(dps),
        vol.Optional(CONF_BRIGHTNESS_LOWER, default=DEFAULT_LOWER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_BRIGHTNESS_UPPER, default=DEFAULT_UPPER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_COLOR_TEMP_LOWER, default=DEFAULT_LOWER_COLOR_TEMP): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_COLOR_TEMP_UPPER, default=DEFAULT_UPPER_COLOR_TEMP): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
    }


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
        self._brightness = None
        self._color_temp = None
        self._hs_color = None
        self._light_mode = None
        self._lower_brightness = self._config.get(
            CONF_BRIGHTNESS_LOWER, DEFAULT_LOWER_BRIGHTNESS
        )
        self._upper_brightness = self._config.get(
            CONF_BRIGHTNESS_UPPER, DEFAULT_UPPER_BRIGHTNESS
        )
        self._lower_color_temp = self._config.get(
            CONF_COLOR_TEMP_LOWER, DEFAULT_LOWER_COLOR_TEMP
        )
        self._upper_color_temp = self._config.get(
            CONF_COLOR_TEMP_UPPER, DEFAULT_UPPER_COLOR_TEMP
        )

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
        if self.has_config(CONF_COLOR_TEMP):
            return self._color_temp
        return None
    
    @property
    def hs_color(self):
        """Return the color of the light."""
        if self.has_config(CONF_HS_COLOR):
            return self._hs_color
        return None
    
    @property
    def light_mode(self):
        """Return the mode of the light."""
        if self.has_config(CONF_LIGHT_MODE):
            return self._light_mode
        return None

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
        supports = 0
        if self.has_config(CONF_BRIGHTNESS):
            supports |= SUPPORT_BRIGHTNESS
        if self.has_config(CONF_COLOR_TEMP):
            supports |= SUPPORT_COLOR_TEMP
        if self.has_config(CONF_HS_COLOR):
            supports |= SUPPORT_COLOR
        return supports
    
    def tuya_hsv_to_hsv(self, hs_color):
        """Convert from tuya hsv format to HA hs + v format"""
        if hs_color is not None:
            h = float(int(hs_color[0:4], 16))
            s = float(map_range(
                    int(hs_color[4:8], 16),
                    0,
                    1000,
                    0,
                    100,
                ))
            v = float(map_range(
                    int(hs_color[8:], 16),
                    self._lower_brightness,
                    self._upper_brightness,
                    0,
                    255,
                ))
            return (h, s, v)
        return None

    def hsv_to_tuya_hsv(self, hs_color):
        """Convert from HA hs + v format to tuya hsv format"""
        if hs_color is not None:
            h = int(hs_color[0])
            s = map_range(
                int(hs_color[1]),
                0,
                100,
                0,
                1000)
            v = map_range(
                int(hs_color[2]),
                0,
                255,
                self._lower_brightness,
                self._upper_brightness
            )
            return f'{h:0>4X}' + f'{s:0>4X}' + f'{v:0>4X}'
        return None

    async def async_turn_on(self, **kwargs):
        """Turn on or control the light."""
        await self._device.set_dp(True, self._dp_id)
        features = self.supported_features

        if ATTR_BRIGHTNESS in kwargs and (features & SUPPORT_BRIGHTNESS):
            brightness = map_range(
                int(kwargs[ATTR_BRIGHTNESS]),
                0,
                255,
                self._lower_brightness,
                self._upper_brightness,
            )
            if self.light_mode == LIGHT_MODES[1]:
                hs_color = self.hs_color
                hs_color = (hs_color[0], hs_color[1], int(kwargs[ATTR_BRIGHTNESS]))
                hs_color = self.hsv_to_tuya_hsv(hs_color)
                await self._device.set_dp(hs_color, self._config.get(CONF_HS_COLOR))
            else:
                await self._device.set_dp(brightness, self._config.get(CONF_BRIGHTNESS))

        if ATTR_HS_COLOR in kwargs and (features & SUPPORT_COLOR):
            hs_color = (kwargs[ATTR_HS_COLOR][0], kwargs[ATTR_HS_COLOR][1], self.brightness)
            hs_color = self.hsv_to_tuya_hsv(hs_color)
            if self.light_mode != LIGHT_MODES[1]:
                await self._device.set_dp(LIGHT_MODES[1], self._config.get(CONF_LIGHT_MODE))
            await self._device.set_dp(hs_color, self._config.get(CONF_HS_COLOR))

        if ATTR_COLOR_TEMP in kwargs and (features & SUPPORT_COLOR_TEMP):
            color_temp = map_range_inverted(
                int(kwargs[ATTR_COLOR_TEMP]),
                MIN_MIRED,
                MAX_MIRED,
                self._lower_color_temp,
                self._upper_color_temp,
            )
            if self.light_mode != LIGHT_MODES[0]:  #If not white mode
                await self._device.set_dp(LIGHT_MODES[0], self._config.get(CONF_LIGHT_MODE))
            await self._device.set_dp(color_temp, self._config.get(CONF_COLOR_TEMP))

    async def async_turn_off(self, **kwargs):
        """Turn Tuya light off."""
        await self._device.set_dp(False, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)
        supported = self.supported_features

        # Get the current light mode
        if supported & self.has_config(CONF_LIGHT_MODE):
            light_mode = self.dps_conf(CONF_LIGHT_MODE)
            self._light_mode = light_mode

        # Get the current color
        if supported & SUPPORT_COLOR:
            hsv_color = self.dps_conf(CONF_HS_COLOR)
            if hsv_color is not None:
                hsv_color = self.tuya_hsv_to_hsv(hsv_color)
            self._hs_color = (hsv_color[0], hsv_color[1])

        # Get the current brightness
        if supported & SUPPORT_BRIGHTNESS:
            if self.light_mode != LIGHT_MODES[1]:  # If not color mode
                brightness = self.dps_conf(CONF_BRIGHTNESS)
            elif self.light_mode == LIGHT_MODES[1]:  # If color mode
                hsv_color = self.dps_conf(CONF_HS_COLOR)
                brightness = int(hsv_color[8:], 16)
            if brightness is not None:
                brightness = map_range(
                    brightness,
                    self._lower_brightness,
                    self._upper_brightness,
                    0,
                    255,
                )
            self._brightness = brightness

        # Get the current color temp
        if supported & SUPPORT_COLOR_TEMP:
            color_temp = self.dps_conf(CONF_COLOR_TEMP)
            if color_temp is not None:
                color_temp = map_range_inverted(
                    color_temp,
                    self._lower_color_temp,
                    self._upper_color_temp,
                    MIN_MIRED,
                    MAX_MIRED,
                )
            self._color_temp = color_temp


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaLight, flow_schema)
