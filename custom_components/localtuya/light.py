"""Platform to locally control Tuya-based light devices."""
import logging
import textwrap
from functools import partial

import homeassistant.util.color as color_util
import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    DOMAIN,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
)
from homeassistant.const import CONF_BRIGHTNESS, CONF_COLOR_TEMP

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR,
    CONF_COLOR_MODE,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_MIN_KELVIN,
)

_LOGGER = logging.getLogger(__name__)

MIRED_TO_KELVIN_CONST = 1000000
DEFAULT_MIN_KELVIN = 2700  # MIRED 370
DEFAULT_MAX_KELVIN = 6500  # MIRED 153

DEFAULT_LOWER_BRIGHTNESS = 29
DEFAULT_UPPER_BRIGHTNESS = 1000


def map_range(value, from_lower, from_upper, to_lower, to_upper):
    """Map a value in one range to another."""
    mapped = (value - from_lower) * (to_upper - to_lower) / (
        from_upper - from_lower
    ) + to_lower
    return round(min(max(mapped, to_lower), to_upper))


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_BRIGHTNESS): vol.In(dps),
        vol.Optional(CONF_COLOR_TEMP): vol.In(dps),
        vol.Optional(CONF_BRIGHTNESS_LOWER, default=DEFAULT_LOWER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_BRIGHTNESS_UPPER, default=DEFAULT_UPPER_BRIGHTNESS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=10000)
        ),
        vol.Optional(CONF_COLOR_MODE): vol.In(dps),
        vol.Optional(CONF_COLOR): vol.In(dps),
        vol.Optional(CONF_COLOR_TEMP_MIN_KELVIN, default=DEFAULT_MIN_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=1500, max=8000)
        ),
        vol.Optional(CONF_COLOR_TEMP_MAX_KELVIN, default=DEFAULT_MAX_KELVIN): vol.All(
            vol.Coerce(int), vol.Range(min=1500, max=8000)
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
        self._lower_brightness = self._config.get(
            CONF_BRIGHTNESS_LOWER, DEFAULT_LOWER_BRIGHTNESS
        )
        self._upper_brightness = self._config.get(
            CONF_BRIGHTNESS_UPPER, DEFAULT_UPPER_BRIGHTNESS
        )
        self._upper_color_temp = self._upper_brightness
        self._max_mired = round(
            MIRED_TO_KELVIN_CONST
            / self._config.get(CONF_COLOR_TEMP_MIN_KELVIN, DEFAULT_MIN_KELVIN)
        )
        self._min_mired = round(
            MIRED_TO_KELVIN_CONST
            / self._config.get(CONF_COLOR_TEMP_MAX_KELVIN, DEFAULT_MAX_KELVIN)
        )
        self._is_white_mode = True  # Hopefully sane default
        self._hs = None

    @property
    def is_on(self):
        """Check if Tuya light is on."""
        return self._state

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return map_range(
            self._brightness, self._lower_brightness, self._upper_brightness, 0, 255
        )

    @property
    def hs_color(self):
        """Return the hs color value."""
        return self._hs

    @property
    def color_temp(self):
        """Return the color_temp of the light."""
        if self.has_config(CONF_COLOR_TEMP):
            return int(
                self._max_mired
                - (
                    ((self._max_mired - self._min_mired) / self._upper_color_temp)
                    * self._color_temp
                )
            )
        return None

    @property
    def min_mireds(self):
        """Return color temperature min mireds."""
        return self._min_mired

    @property
    def max_mireds(self):
        """Return color temperature max mireds."""
        return self._max_mired

    @property
    def supported_features(self):
        """Flag supported features."""
        supports = 0
        if self.has_config(CONF_BRIGHTNESS):
            supports |= SUPPORT_BRIGHTNESS
        if self.has_config(CONF_COLOR_TEMP):
            supports |= SUPPORT_COLOR_TEMP
        if self.has_config(CONF_COLOR):
            supports |= SUPPORT_COLOR | SUPPORT_BRIGHTNESS
        return supports

    def __is_color_rgb_encoded(self):
        return len(self.dps_conf(CONF_COLOR)) > 12

    async def async_turn_on(self, **kwargs):
        """Turn on or control the light."""
        states = {}
        states[self._dp_id] = True
        features = self.supported_features
        if ATTR_BRIGHTNESS in kwargs and (features & SUPPORT_BRIGHTNESS):
            brightness = map_range(
                int(kwargs[ATTR_BRIGHTNESS]),
                0,
                255,
                self._lower_brightness,
                self._upper_brightness,
            )
            if self._is_white_mode:
                states[self._config.get(CONF_BRIGHTNESS)] = brightness

            else:
                if self.__is_color_rgb_encoded():
                    rgb = color_util.color_hsv_to_RGB(
                        self._hs[0],
                        self._hs[1],
                        int(brightness * 100 / self._upper_brightness),
                    )
                    color = "{:02x}{:02x}{:02x}{:04x}{:02x}{:02x}".format(
                        round(rgb[0]),
                        round(rgb[1]),
                        round(rgb[2]),
                        round(self._hs[0]),
                        round(self._hs[1] * 255 / 100),
                        brightness,
                    )
                else:
                    color = "{:04x}{:04x}{:04x}".format(
                        round(self._hs[0]), round(self._hs[1] * 10.0), brightness
                    )
                states[self._config.get(CONF_COLOR)] = color

        if ATTR_HS_COLOR in kwargs and (features & SUPPORT_COLOR):
            hs = kwargs[ATTR_HS_COLOR]
            if self.__is_color_rgb_encoded():
                rgb = color_util.color_hsv_to_RGB(
                    hs[0], hs[1], int(self._brightness * 100 / self._upper_brightness)
                )
                color = "{:02x}{:02x}{:02x}{:04x}{:02x}{:02x}".format(
                    round(rgb[0]),
                    round(rgb[1]),
                    round(rgb[2]),
                    round(hs[0]),
                    round(hs[1] * 255 / 100),
                    self._brightness,
                )
            else:
                color = "{:04x}{:04x}{:04x}".format(
                    round(hs[0]), round(hs[1] * 10.0), self._brightness
                )
            states[self._config.get(CONF_COLOR)] = color
            if self._is_white_mode:
                states[self._config.get(CONF_COLOR_MODE)] = "colour"

        if ATTR_COLOR_TEMP in kwargs and (features & SUPPORT_COLOR_TEMP):
            color_temp = int(
                self._upper_color_temp
                - (self._upper_color_temp / (self._max_mired - self._min_mired))
                * (int(kwargs[ATTR_COLOR_TEMP]) - self._min_mired)
            )
            if not self._is_white_mode:
                states[self._config.get(CONF_COLOR_MODE)] = "white"
                states[self._config.get(CONF_BRIGHTNESS)] = self._brightness
            states[self._config.get(CONF_COLOR_TEMP)] = color_temp

        await self._device.set_dps(states)

    async def async_turn_off(self, **kwargs):
        """Turn Tuya light off."""
        await self._device.set_dp(False, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)
        supported = self.supported_features

        if supported & SUPPORT_COLOR:
            self._is_white_mode = self.dps_conf(CONF_COLOR_MODE) == "white"
            if self._is_white_mode:
                self._hs = [0, 0]

        if self._is_white_mode:
            if supported & SUPPORT_BRIGHTNESS:
                self._brightness = self.dps_conf(CONF_BRIGHTNESS)
        else:
            color = self.dps_conf(CONF_COLOR)
            if color is not None:
                if self.__is_color_rgb_encoded():
                    hue = int(color[6:10], 16)
                    sat = int(color[10:12], 16)
                    value = int(color[12:14], 16)
                    self._hs = [hue, (sat * 100 / 255)]
                    self._brightness = value
                else:
                    hue, sat, value = [
                        int(value, 16) for value in textwrap.wrap(color, 4)
                    ]
                    self._hs = [hue, sat / 10.0]
                    self._brightness = value

        if supported & SUPPORT_COLOR_TEMP:
            self._color_temp = self.dps_conf(CONF_COLOR_TEMP)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaLight, flow_schema)
