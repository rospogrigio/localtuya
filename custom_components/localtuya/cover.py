"""Platform to locally control Tuya-based cover devices."""
import asyncio
import logging
import time
from functools import partial

import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN,
    CoverEntityFeature,
    CoverEntity,
    DEVICE_CLASSES_SCHEMA,
)
from homeassistant.const import CONF_DEVICE_CLASS
from .config_flow import _col_to_select
from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_COMMANDS_SET,
    CONF_CURRENT_POSITION_DP,
    CONF_POSITION_INVERTED,
    CONF_POSITIONING_MODE,
    CONF_SET_POSITION_DP,
    CONF_SPAN_TIME,
)


# cover states.
STATE_OPENING = "opening"
STATE_CLOSING = "closing"
STATE_STOPPED = "stopped"
STATE_SET_CMD = "moving"
STATE_SET_OPENING = "set_opeing"
STATE_SET_CLOSING = "set_closing"

_LOGGER = logging.getLogger(__name__)


COVER_COMMANDS = {
    "Open, Close and Stop": "open_close_stop",
    "ON, OFF and Stop": "on_off_stop",
    "fz, zz and Stop": "fz_zz_stop",
    "1, 2 and 3": "1_2_3",
    "0, 1 and 2": "0_1_2",
}

MODE_NONE = "none"
MODE_SET_POSITION = "position"
MODE_TIME_BASED = "timed"
COVER_MODES = {
    "Neither": MODE_NONE,
    "Set Position": MODE_SET_POSITION,
    "Time Based": MODE_TIME_BASED,
}

COVER_TIMEOUT_TOLERANCE = 3.0

DEF_CMD_SET = list(COVER_COMMANDS.values())[0]
DEF_POS_MODE = list(COVER_MODES.values())[0]
DEFAULT_SPAN_TIME = 25.0


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_COMMANDS_SET, default=DEF_CMD_SET): _col_to_select(
            COVER_COMMANDS
        ),
        vol.Optional(CONF_POSITIONING_MODE, default=DEF_POS_MODE): _col_to_select(
            COVER_MODES
        ),
        vol.Optional(CONF_CURRENT_POSITION_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_SET_POSITION_DP): _col_to_select(dps, is_dps=True),
        vol.Optional(CONF_POSITION_INVERTED, default=False): bool,
        vol.Optional(CONF_SPAN_TIME, default=DEFAULT_SPAN_TIME): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=300.0)
        ),
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }


class LocaltuyaCover(LocalTuyaEntity, CoverEntity):
    """Tuya cover device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaCover."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        commands_set = DEF_CMD_SET
        if self.has_config(CONF_COMMANDS_SET):
            commands_set = self._config[CONF_COMMANDS_SET]
        self._open_cmd = commands_set.split("_")[0]
        self._close_cmd = commands_set.split("_")[1]
        self._stop_cmd = commands_set.split("_")[2]
        self._timer_start = time.time()
        self._state = self._stop_cmd
        self._previous_state = self._state
        self._current_cover_position = 0
        self._current_state_action = STATE_STOPPED  # Default.
        self._set_new_position = int | None

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )
        if self._config[CONF_POSITIONING_MODE] != MODE_NONE:
            supported_features = supported_features | CoverEntityFeature.SET_POSITION
        return supported_features

    @property
    def _current_state(self) -> str:
        """Return the current state of the cover."""
        state = self._current_state_action
        curr_pos = self.current_cover_position
        # Reset STATE when cover is fully closed or fully opened.
        if (state == STATE_CLOSING and curr_pos == 0) or (
            state == STATE_OPENING and curr_pos == 100
        ):
            self._current_state_action = STATE_STOPPED
        # in case cover moving by set position cmd.
        if (
            self._current_state_action == STATE_SET_CLOSING
            or self._current_state_action == STATE_SET_OPENING
        ):
            set_pos = self._set_new_position
            # Reset state whenn cover reached the position.
            if curr_pos - set_pos < 5 and curr_pos - set_pos >= -5:
                self._current_state_action = STATE_STOPPED
        return self._current_state_action

    @property
    def current_cover_position(self):
        """Return current cover position in percent."""
        if self._config[CONF_POSITIONING_MODE] == MODE_NONE:
            return None
        return self._current_cover_position

    @property
    def is_opening(self):
        """Return if cover is opening."""
        state = self._current_state
        return state == STATE_SET_OPENING or state == STATE_OPENING

    @property
    def is_closing(self):
        """Return if cover is closing."""
        state = self._current_state
        return state == STATE_SET_CLOSING or state == STATE_CLOSING

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self._config[CONF_POSITIONING_MODE] == MODE_NONE:
            return None
        return self.current_cover_position == 0 and self._current_state == STATE_STOPPED

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        # Update device values IF the device is moving at the moment.
        if self._current_state != STATE_STOPPED:
            await self.async_stop_cover()

        self.debug("Setting cover position: %r", kwargs[ATTR_POSITION])
        if self._config[CONF_POSITIONING_MODE] == MODE_TIME_BASED:
            newpos = float(kwargs[ATTR_POSITION])

            currpos = self.current_cover_position
            posdiff = abs(newpos - currpos)
            mydelay = posdiff / 100.0 * self._config[CONF_SPAN_TIME]
            if newpos > currpos:
                self.debug("Opening to %f: delay %f", newpos, mydelay)
                await self.async_open_cover()
                self.update_state(STATE_OPENING)
            else:
                self.debug("Closing to %f: delay %f", newpos, mydelay)
                await self.async_close_cover()
                self.update_state(STATE_CLOSING)
            self.hass.async_create_task(self.async_stop_after_timeout(mydelay))
            self.debug("Done")

        elif self._config[CONF_POSITIONING_MODE] == MODE_SET_POSITION:
            converted_position = int(kwargs[ATTR_POSITION])
            if self._config.get(CONF_POSITION_INVERTED):
                converted_position = 100 - converted_position
            if 0 <= converted_position <= 100 and self.has_config(CONF_SET_POSITION_DP):
                await self._device.set_dp(
                    converted_position, self._config[CONF_SET_POSITION_DP]
                )
            # Give it a moment, to make sure hass updated current pos.
            await asyncio.sleep(0.1)
            self.update_state(STATE_SET_CMD, converted_position)

    async def async_stop_after_timeout(self, delay_sec):
        """Stop the cover if timeout (max movement span) occurred."""
        await asyncio.sleep(delay_sec)
        await self.async_stop_cover()

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self.debug("Launching command %s to cover ", self._open_cmd)
        await self._device.set_dp(self._open_cmd, self._dp_id)
        if self._config[CONF_POSITIONING_MODE] == MODE_TIME_BASED:
            # for timed positioning, stop the cover after a full opening timespan
            # instead of waiting the internal timeout
            self.hass.async_create_task(
                self.async_stop_after_timeout(
                    self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
                )
            )
        self.update_state(STATE_OPENING)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        self.debug("Launching command %s to cover ", self._close_cmd)
        await self._device.set_dp(self._close_cmd, self._dp_id)
        if self._config[CONF_POSITIONING_MODE] == MODE_TIME_BASED:
            # for timed positioning, stop the cover after a full opening timespan
            # instead of waiting the internal timeout
            self.hass.async_create_task(
                self.async_stop_after_timeout(
                    self._config[CONF_SPAN_TIME] + COVER_TIMEOUT_TOLERANCE
                )
            )
        self.update_state(STATE_CLOSING)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.debug("Launching command %s to cover ", self._stop_cmd)
        await self._device.set_dp(self._stop_cmd, self._dp_id)
        self.update_state(STATE_STOPPED)

    def status_restored(self, stored_state):
        """Restore the last stored cover status."""
        if self._config[CONF_POSITIONING_MODE] == MODE_TIME_BASED:
            stored_pos = stored_state.attributes.get("current_position")
            if stored_pos is not None:
                self._current_cover_position = stored_pos
                self.debug("Restored cover position %s", self._current_cover_position)

    def status_updated(self):
        """Device status was updated."""
        self._previous_state = self._state
        self._state = self.dp_value(self._dp_id)
        if self._state.isupper():
            self._open_cmd = self._open_cmd.upper()
            self._close_cmd = self._close_cmd.upper()
            self._stop_cmd = self._stop_cmd.upper()

        if self.has_config(CONF_CURRENT_POSITION_DP):
            curr_pos = self.dp_value(CONF_CURRENT_POSITION_DP)
            if self._config.get(CONF_POSITION_INVERTED):
                self._current_cover_position = 100 - curr_pos
            else:
                self._current_cover_position = curr_pos
        if (
            self._config[CONF_POSITIONING_MODE] == MODE_TIME_BASED
            and self._state != self._previous_state
        ):
            if self._previous_state != self._stop_cmd:
                # the state has changed, and the cover was moving
                time_diff = time.time() - self._timer_start
                pos_diff = round(time_diff / self._config[CONF_SPAN_TIME] * 100.0)
                if self._previous_state == self._close_cmd:
                    pos_diff = -pos_diff
                self._current_cover_position = min(
                    100, max(0, self._current_cover_position + pos_diff)
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

        # Keep record in last_state as long as not during connection/re-connection,
        # as last state will be used to restore the previous state
        if (self._state is not None) and (not self._device.is_connecting):
            self._last_state = self._state

    def update_state(self, action, position=None):
        """Update cover current states."""
        state = self._current_state_action
        # using Commands.
        if position is None:
            self._current_state_action = action
        # Set position cmd, check if target position weither close or open
        if action == STATE_SET_CMD and position is not None:
            curr_pos = self.current_cover_position
            self._set_new_position = position
            pos_diff = position - curr_pos
            # Prevent stuck state when interrupted on middle of cmd
            if state == STATE_STOPPED:
                if pos_diff > 0:
                    self._current_state_action = STATE_SET_OPENING
                elif pos_diff < 0:
                    self._current_state_action = STATE_SET_CLOSING
            else:
                self._current_state_action = STATE_STOPPED
        # Write state data.
        self.async_write_ha_state()


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaCover, flow_schema)
