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

_LOGGER = logging.getLogger(__name__)

MIN_MIRED = 153
MAX_MIRED = 370


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_BRIGHTNESS): vol.In(dps),
        vol.Optional(CONF_COLOR_TEMP): vol.In(dps),
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
            supports = supports | SUPPORT_COLOR_TEMP
        return supports

    async def async_turn_on(self, **kwargs):
        """Turn on or control the light."""
        await self._device.set_dps(True, self._dps_id)

        if ATTR_BRIGHTNESS in kwargs:
            await self._device.set_dps(
                max(int(kwargs[ATTR_BRIGHTNESS]), 25), self._config.get(CONF_BRIGHTNESS)
            )

        if ATTR_HS_COLOR in kwargs:
            raise ValueError(" TODO implement RGB from HS")

        if ATTR_COLOR_TEMP in kwargs:
            color_temp = int(
                255
                - (255 / (MAX_MIRED - MIN_MIRED))
                * (int(kwargs[ATTR_COLOR_TEMP]) - MIN_MIRED)
            )
            await self._device.set_dps(color_temp, self._config.get(CONF_COLOR_TEMP))

    async def async_turn_off(self, **kwargs):
        """Turn Tuya light off."""
        await self._device.set_dps(False, self._dps_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dps_id)

        brightness = self.dps_conf(CONF_BRIGHTNESS)
        if brightness is not None:
            brightness = min(brightness, 255)
            brightness = max(brightness, 25)
        self._brightness = brightness

        self._color_temp = self.dps_conf(CONF_COLOR_TEMP)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaLight, flow_schema)
