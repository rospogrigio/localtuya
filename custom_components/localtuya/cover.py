"""Platform to locally control Tuya-based cover devices."""
import asyncio
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_COMMANDS_SET,
    CONF_CURRENT_POSITION_DP,
    CONF_POSITION_INVERTED,
    CONF_POSITIONING_MODE,
    CONF_SET_POSITION_DP,
    CONF_SPAN_TIME,
)

_LOGGER = logging.getLogger(__name__)

COVER_ONOFF_CMDS = "on_off_stop"
COVER_OPENCLOSE_CMDS = "open_close_stop"
COVER_FZZZ_CMDS = "fz_zz_stop"
COVER_12_CMDS = "1_2_3"
COVER_MODE_NONE = "none"
COVER_MODE_POSITION = "position"
COVER_MODE_FAKE = "fake"

DEFAULT_COMMANDS_SET = COVER_ONOFF_CMDS
DEFAULT_POSITIONING_MODE = COVER_MODE_NONE
DEFAULT_SPAN_TIME = 25.0


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_COMMANDS_SET): vol.In(
            [COVER_ONOFF_CMDS, COVER_OPENCLOSE_CMDS, COVER_FZZZ_CMDS, COVER_12_CMDS]
        ),
        vol.Optional(CONF_POSITIONING_MODE, default=DEFAULT_POSITIONING_MODE): vol.In(
            [COVER_MODE_NONE, COVER_MODE_POSITION, COVER_MODE_FAKE]
        ),
        vol.Optional(CONF_CURRENT_POSITION_DP): vol.In(dps),
        vol.Optional(CONF_SET_POSITION_DP): vol.In(dps),
        vol.Optional(CONF_POSITION_INVERTED, default=False): bool,
        vol.Optional(CONF_SPAN_TIME, default=DEFAULT_SPAN_TIME): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=300.0)
        ),
    }


class LocaltuyaCover(LocalTuyaEntity, CoverEntity):
    """Tuya cover device."""

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize a new LocaltuyaCover."""
        super().__init__(device, config_entry, switchid, **kwargs)
        self._state = None
        self._current_cover_position = None
        commands_set = DEFAULT_COMMANDS_SET
        if self.has_config(CONF_COMMANDS_SET):
            commands_set = self._config[CONF_COMMANDS_SET]
        self._open_cmd = commands_set.split("_")[0]
        self._close_cmd = commands_set.split("_")[1]
        self._stop_cmd = commands_set.split("_")[2]
        print("Initialized cover [{}]".format(self.name))

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
        if self._config[CONF_POSITIONING_MODE] != COVER_MODE_NONE:
            supported_features = supported_features | SUPPORT_SET_POSITION
        return supported_features

    @property
    def current_cover_position(self):
        """Return current cover position in percent."""
        return self._current_cover_position

    @property
    def is_opening(self):
        """Return if cover is opening."""
        state = self._state
        return state == self._open_cmd

    @property
    def is_closing(self):
        """Return if cover is closing."""
        state = self._state
        return state == self._close_cmd

    @property
    def is_open(self):
        """Return if the cover is open or not."""
        if self._config[CONF_POSITIONING_MODE] != COVER_MODE_POSITION:
            return None

        return self._current_cover_position == 100

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self._config[CONF_POSITIONING_MODE] != COVER_MODE_POSITION:
            return None

        return self._current_cover_position == 0

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.debug("Setting cover position: %r", kwargs[ATTR_POSITION])
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_FAKE:
            newpos = float(kwargs[ATTR_POSITION])

            currpos = self.current_cover_position
            posdiff = abs(newpos - currpos)
            mydelay = posdiff / 50.0 * self._config[CONF_SPAN_TIME]
            if newpos > currpos:
                _LOGGER.debug("Opening to %f: delay %f", newpos, mydelay)
                await self.async_open_cover()
            else:
                _LOGGER.debug("Closing to %f: delay %f", newpos, mydelay)
                await self.async_close_cover()
            await asyncio.sleep(mydelay)
            await self.async_stop_cover()
            self._current_cover_position = 50
            _LOGGER.debug("Done")

        elif self._config[CONF_POSITIONING_MODE] == COVER_MODE_POSITION:
            converted_position = int(kwargs[ATTR_POSITION])
            if self._config[CONF_POSITION_INVERTED]:
                converted_position = 100 - converted_position

            if 0 <= converted_position <= 100 and self.has_config(CONF_SET_POSITION_DP):
                await self._device.set_dp(
                    converted_position, self._config[CONF_SET_POSITION_DP]
                )

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Launching command %s to cover ", self._open_cmd)
        await self._device.set_dp(self._open_cmd, self._dp_id)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        _LOGGER.debug("Launching command %s to cover ", self._close_cmd)
        await self._device.set_dp(self._close_cmd, self._dp_id)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("Launching command %s to cover ", self._stop_cmd)
        await self._device.set_dp(self._stop_cmd, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)
        if self._state.isupper():
            self._open_cmd = self._open_cmd.upper()
            self._close_cmd = self._close_cmd.upper()
            self._stop_cmd = self._stop_cmd.upper()

        if self.has_config(CONF_CURRENT_POSITION_DP):
            curr_pos = self.dps_conf(CONF_CURRENT_POSITION_DP)
            if self._config[CONF_POSITION_INVERTED]:
                self._current_cover_position = 100 - curr_pos
            else:
                self._current_cover_position = curr_pos
        else:
            self._current_cover_position = 50


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaCover, flow_schema)
