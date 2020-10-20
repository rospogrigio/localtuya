"""Platform to locally control Tuya-based light devices."""
import logging
from functools import partial

import voluptuous as vol

from homeassistant.const import (
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
)
from homeassistant.components.light import (
    LightEntity,
    DOMAIN,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_BRIGHTNESS_LOWER, CONF_BRIGHTNESS_UPPER

_LOGGER = logging.getLogger(__name__)

MIN_MIRED = 153
MAX_MIRED = 370

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
            return int(MAX_MIRED - (((MAX_MIRED - MIN_MIRED) / 255) * self._color_temp))
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
        return supports

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
            await self._device.set_dp(brightness, self._config.get(CONF_BRIGHTNESS))

        if ATTR_HS_COLOR in kwargs:
            raise ValueError(" TODO implement RGB from HS")

        if ATTR_COLOR_TEMP in kwargs and (features & SUPPORT_COLOR_TEMP):
            color_temp = int(
                255
                - (255 / (MAX_MIRED - MIN_MIRED))
                * (int(kwargs[ATTR_COLOR_TEMP]) - MIN_MIRED)
            )
            await self._device.set_dp(color_temp, self._config.get(CONF_COLOR_TEMP))

    async def async_turn_off(self, **kwargs):
        """Turn Tuya light off."""
        await self._device.set_dp(False, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)
        supported = self.supported_features

        if supported & SUPPORT_BRIGHTNESS:
            brightness = self.dps_conf(CONF_BRIGHTNESS)
            if brightness is not None:
                brightness = map_range(
                    brightness,
                    self._lower_brightness,
                    self._upper_brightness,
                    0,
                    255,
                )
            self._brightness = brightness

        if supported & SUPPORT_COLOR_TEMP:
            self._color_temp = self.dps_conf(CONF_COLOR_TEMP)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaLight, flow_schema)
