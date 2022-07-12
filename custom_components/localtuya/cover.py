"""Platform to locally control Tuya-based cover devices."""
import asyncio
import logging
import time
from functools import partial
from typing import Any

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
COVER_MODE_TIMED = "timed"
COVER_TIMEOUT_TOLERANCE = 3.0

DEFAULT_COMMANDS_SET = COVER_ONOFF_CMDS
DEFAULT_POSITIONING_MODE = COVER_MODE_NONE
DEFAULT_SPAN_TIME = 25.0

COVER_MIN_POSITION = 0
COVER_MAX_POSITION = 100

def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_COMMANDS_SET): vol.In(
            [COVER_ONOFF_CMDS, COVER_OPENCLOSE_CMDS, COVER_FZZZ_CMDS, COVER_12_CMDS]
        ),
        vol.Optional(CONF_POSITIONING_MODE, default=DEFAULT_POSITIONING_MODE): vol.In(
            [COVER_MODE_NONE, COVER_MODE_POSITION, COVER_MODE_TIMED]
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

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaCover."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        commands_set = DEFAULT_COMMANDS_SET
        if self.has_config(CONF_COMMANDS_SET):
            commands_set = self._config[CONF_COMMANDS_SET]

        if self._config[CONF_POSITION_INVERTED] is not None:
            if self._config[CONF_POSITION_INVERTED] :
                self._open_cmd = commands_set.split("_")[1]
                self._close_cmd = commands_set.split("_")[0]
            else:
                self._open_cmd = commands_set.split("_")[0]
                self._close_cmd = commands_set.split("_")[1]
        self._stop_cmd = commands_set.split("_")[2]
        self._timer_start = time.time()
        self._state = self._stop_cmd
        self._previous_state = self._state
        self._current_cover_position = 0
        _LOGGER.debug("Initialized cover [%s]", self.name)

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
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_NONE:
            return None

        reverse = False
        if self._config[CONF_POSITION_INVERTED] is not None:
            reverse = self._config[CONF_POSITION_INVERTED]

        if reverse:
            position = COVER_MAX_POSITION - self._current_cover_position
        else:
            position = self._current_cover_position

        self._current_cover_position = position
        return position

    def _get_current_cover_position(self, value, from_min=0, from_max=255,reverse=False) -> int:
        to_min = 0
        to_max = 255

        if reverse:
            value = from_max - value + from_min

        return ((value - from_min) / (from_max - from_min)) * (to_max - to_min) + to_min

    @property
    def current_cover_tilt_position(self) -> int:
        """Return current cover position in percent."""
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_NONE:
            return None

        reverse = False
        if self._config[CONF_POSITION_INVERTED] is not None:
            reverse = self._config[CONF_POSITION_INVERTED]

        if reverse:
            position = self._current_cover_position
        else:
            position = COVER_MAX_POSITION - self._current_cover_position


        self._current_cover_position = position
        return position

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
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_NONE:
            return None
        current_position = self._current_cover_position

        if self._config[CONF_POSITION_INVERTED]:
            current_position = COVER_MAX_POSITION - self._current_cover_position

        if current_position == COVER_MIN_POSITION:
            return True
        if current_position == COVER_MAX_POSITION:
            return False
        return None

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        self.debug("Setting cover position: %r", kwargs[ATTR_POSITION])
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            newpos = float(kwargs[ATTR_POSITION])

            currpos = self.current_cover_position
            posdiff = abs(newpos - currpos)
            mydelay = posdiff / 100.0 * self._config[CONF_SPAN_TIME]
            if newpos > currpos:
                self.debug("Opening to %f: delay %f", newpos, mydelay)
                await self.async_open_cover()
            else:
                self.debug("Closing to %f: delay %f", newpos, mydelay)
                await self.async_close_cover()
            self.hass.async_create_task(self.async_stop_after_timeout(mydelay))
            self.debug("Done")

        elif self._config[CONF_POSITIONING_MODE] == COVER_MODE_POSITION:
            converted_position = int(kwargs[ATTR_POSITION])
            if COVER_MIN_POSITION <= converted_position <= COVER_MAX_POSITION and self.has_config(CONF_SET_POSITION_DP):
                await self._device.set_dp(
                    converted_position, self._config[CONF_SET_POSITION_DP]
                )

    async def async_stop_after_timeout(self, delay_sec):
        """Stop the cover if timeout (max movement span) occurred."""
        await asyncio.sleep(delay_sec)
        await self.async_stop_cover()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self.debug("Launching command %s to cover ", self._open_cmd)
        await self._device.set_dp(self._open_cmd, self._dp_id)
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            # for timed positioning, stop the cover after a full opening timespan
            # instead of waiting the internal timeout
            self.hass.async_create_task(
                self.async_stop_after_timeout(
                    self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
                )
            )
        await self._device.set_dp(COVER_MAX_POSITION, self._config[CONF_SET_POSITION_DP])

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        self.debug("Launching command %s to cover ", self._close_cmd)
        await self._device.set_dp(self._close_cmd, self._dp_id)
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            # for timed positioning, stop the cover after a full opening timespan
            # instead of waiting the internal timeout
            self.hass.async_create_task(
                self.async_stop_after_timeout(
                    self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
                )
            )

        await self._device.set_dp(COVER_MIN_POSITION, self._config[CONF_SET_POSITION_DP])
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.debug("Launching command %s to cover ", self._stop_cmd)
        await self._device.set_dp(self._stop_cmd, self._dp_id)



    def status_restored(self, stored_state):
        """Restore the last stored cover status."""
        if self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED:
            stored_pos = stored_state.attributes.get("current_position")
            if stored_pos is not None:
                self._current_cover_position = stored_pos
                self.debug("Restored cover position %s", self._current_cover_position)

    def status_updated(self):
        """Device status was updated."""
        self._previous_state = self._state
        self._state = self.dps(self._dp_id)

        if self._state is not None:
            if self._state.isupper():
                self._open_cmd = self._open_cmd.upper()
                self._close_cmd = self._close_cmd.upper()
                self._stop_cmd = self._stop_cmd.upper()

        if self.has_config(CONF_CURRENT_POSITION_DP):
            curr_pos = self.dps_conf(CONF_CURRENT_POSITION_DP)
            if curr_pos is not None:
                if self._config[CONF_POSITION_INVERTED]:
                    self._current_cover_position = COVER_MAX_POSITION - curr_pos
                else:
                    self._current_cover_position = curr_pos

            if self._current_cover_position is not None:
                if self._current_cover_position == COVER_MIN_POSITION:
                    self._state = self._open_cmd.upper()
                elif self._current_cover_position == COVER_MAX_POSITION:
                    self._state = self._close_cmd.upper()
                else:
                    self._state = self._stop_cmd.upper()
        # time based
        if (
            self._config[CONF_POSITIONING_MODE] == COVER_MODE_TIMED
            and self._state != self._previous_state
        ):
            if self._previous_state != self._stop_cmd:
                # the state has changed, and the cover was moving
                time_diff = time.time() - self._timer_start
                pos_diff = round(time_diff / self._config[CONF_SPAN_TIME] * 100.0)
                if self._previous_state == self._close_cmd:
                    pos_diff = -pos_diff
                self._current_cover_position = min(
                    COVER_MAX_POSITION, max(COVER_MIN_POSITION, self._current_cover_position + pos_diff)
                )

                change = "stopped" if self._state == self._stop_cmd else "inverted"
                self.debug(
                    "Movement %s after %s sec., position difference %s",
                    change,
                    time_diff,
                    pos_diff,
                )

            # store the time of the last movement change
            self._timer_start = time.time()


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaCover, flow_schema)
