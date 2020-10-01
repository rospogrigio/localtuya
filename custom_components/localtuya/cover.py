"""Platform to locally control Tuya-based cover devices."""
import logging
from time import sleep

import voluptuous as vol

from homeassistant.components.cover import (
    CoverEntity,
    DOMAIN,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
    ATTR_POSITION,
)
from homeassistant.const import CONF_ID

from .const import (
    CONF_OPEN_CMD,
    CONF_CLOSE_CMD,
    CONF_STOP_CMD,
    CONF_CURRPOS,
    CONF_SETPOS,
    CONF_POSITIONING_MODE,
    CONF_MODE_NONE,
    CONF_MODE_YES,
    CONF_MODE_FAKE,
    CONF_SPAN_TIME,
)
from .common import LocalTuyaEntity, prepare_setup_entities

_LOGGER = logging.getLogger(__name__)

DEFAULT_OPEN_CMD = "on"
DEFAULT_CLOSE_CMD = "off"
DEFAULT_STOP_CMD = "stop"
DEFAULT_POSITIONING_MODE = CONF_MODE_NONE
DEFAULT_SPAN_TIME = 25.0


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_OPEN_CMD, default=DEFAULT_OPEN_CMD): vol.In(
            ["on", "open"]
        ),
        vol.Optional(CONF_CLOSE_CMD, default=DEFAULT_CLOSE_CMD): vol.In(
            ["off", "close"]
        ),
        vol.Optional(CONF_POSITIONING_MODE, default=DEFAULT_POSITIONING_MODE): vol.In(
            [CONF_MODE_NONE, CONF_MODE_YES, CONF_MODE_FAKE]
        ),
        vol.Optional(CONF_CURRPOS): vol.In(dps),
        vol.Optional(CONF_SETPOS): vol.In(dps),
        vol.Optional(CONF_SPAN_TIME, default=DEFAULT_SPAN_TIME): float,
    }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up a Tuya cover based on a config entry."""
    tuyainterface, entities_to_setup = prepare_setup_entities(
        hass, config_entry, DOMAIN
    )
    if not entities_to_setup:
        return

    covers = []
    for device_config in entities_to_setup:
        covers.append(
            LocaltuyaCover(
                tuyainterface,
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(covers)


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
        self._current_cover_position = 50
        self._config[CONF_STOP_CMD] = DEFAULT_STOP_CMD
        print(
            "Initialized cover [{}] with status [{}] and state [{}]".format(
                self.name, self._status, self._state
            )
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
        if self._config[CONF_POSITIONING_MODE] != CONF_MODE_NONE:
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
        return state == self._config[CONF_OPEN_CMD]

    @property
    def is_closing(self):
        """Return if cover is closing."""
        state = self._state
        return state == self._config[CONF_CLOSE_CMD]

    @property
    def is_open(self):
        """Return if the cover is open or not."""
        if self._config[CONF_POSITIONING_MODE] != CONF_MODE_YES:
            return None
        else:
            return self._current_cover_position == 100

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        if self._config[CONF_POSITIONING_MODE] != CONF_MODE_YES:
            return None
        else:
            return self._current_cover_position == 0

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.debug("Setting cover position: %r", kwargs[ATTR_POSITION])
        if self._config[CONF_POSITIONING_MODE] == CONF_MODE_FAKE:
            newpos = float(kwargs[ATTR_POSITION])

            currpos = self.current_cover_position
            posdiff = abs(newpos - currpos)
            mydelay = posdiff / 50.0 * self._config[CONF_SPAN_TIME]
            if newpos > currpos:
                _LOGGER.debug("Opening to %f: delay %f", newpos, mydelay)
                self.open_cover()
            else:
                _LOGGER.debug("Closing to %f: delay %f", newpos, mydelay)
                self.close_cover()
            sleep(mydelay)
            self.stop_cover()
            self._current_cover_position = 50
            _LOGGER.debug("Done")

        elif self._config[CONF_POSITIONING_MODE] == CONF_MODE_YES:
            converted_position = int(kwargs[ATTR_POSITION])
            if converted_position in range(0, 101) and self.has_config(CONF_SETPOS):
                self._device.set_dps(converted_position, self._config[CONF_SETPOS])

    def open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Launching command %s to cover ", self._config[CONF_OPEN_CMD])
        self._device.set_dps(self._config[CONF_OPEN_CMD], self._dps_id)

    def close_cover(self, **kwargs):
        """Close cover."""
        _LOGGER.debug("Launching command %s to cover ", self._config[CONF_CLOSE_CMD])
        self._device.set_dps(self._config[CONF_CLOSE_CMD], self._dps_id)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("Launching command %s to cover ", self._config[CONF_STOP_CMD])
        self._device.set_dps(self._config[CONF_STOP_CMD], self._dps_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dps_id)
        if self.has_config(CONF_CURRPOS):
            self._current_cover_position = self.dps(self._config[CONF_CURRPOS])
