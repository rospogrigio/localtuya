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
)
from homeassistant.const import CONF_ID

from .const import (
    CONF_OPEN_CMD,
    CONF_CLOSE_CMD,
    CONF_STOP_CMD,
)
from .common import LocalTuyaEntity, prepare_setup_entities

_LOGGER = logging.getLogger(__name__)

DEFAULT_OPEN_CMD = "on"
DEFAULT_CLOSE_CMD = "off"
DEFAULT_STOP_CMD = "stop"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_OPEN_CMD, default=DEFAULT_OPEN_CMD): str,
        vol.Optional(CONF_CLOSE_CMD, default=DEFAULT_CLOSE_CMD): str,
        vol.Optional(CONF_STOP_CMD, default=DEFAULT_STOP_CMD): str,
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
        self._position = 50
        print(
            "Initialized cover [{}] with status [{}] and state [{}]".format(
                self.name, self._status, self._state
            )
        )

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = (
            SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION
        )
        return supported_features

    @property
    def current_cover_position(self):
        """Return current cover position in percent."""
        # self.update()
        # state = self._state
        #        _LOGGER.info("curr_pos() : %i", self._position)
        # print('curr_pos() : state [{}]'.format(state))
        return self._position

    @property
    def is_opening(self):
        """Return if cover is opening."""
        # self.update()
        state = self._state
        # print('is_opening() : state [{}]'.format(state))
        if state == "on":
            return True
        return False

    @property
    def is_closing(self):
        """Return if cover is closing."""
        # self.update()
        state = self._state
        # print('is_closing() : state [{}]'.format(state))
        if state == "off":
            return True
        return False

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        # _LOGGER.info("running is_closed from cover")
        # self.update()
        state = self._state
        # print('is_closed() : state [{}]'.format(state))
        if state == "off":
            return False
        if state == "on":
            return True
        return None

    def set_cover_position(self, **kwargs):
        # _LOGGER.info("running set_cover_position from cover")
        """Move the cover to a specific position."""
        newpos = float(kwargs["position"])
        #        _LOGGER.info("Set new pos: %f", newpos)

        currpos = self.current_cover_position
        posdiff = abs(newpos - currpos)
        #       25 sec corrisponde alla chiusura/apertura completa
        mydelay = posdiff / 2.0
        if newpos > currpos:
            #            _LOGGER.info("Opening to %f: delay %f", newpos, mydelay )
            self.open_cover()
        else:
            #            _LOGGER.info("Closing to %f: delay %f", newpos, mydelay )
            self.close_cover()
        sleep(mydelay)
        self.stop_cover()
        self._position = 50  # newpos

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
