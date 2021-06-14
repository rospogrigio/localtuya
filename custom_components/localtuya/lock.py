"""Platform to locally control Tuya-based lock devices."""
import asyncio
import logging
import time
from functools import partial

import voluptuous as vol
from homeassistant.components.lock import DOMAIN, SUPPORT_OPEN, LockEntity

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_LOCK_COMMANDS_SET

_LOGGER = logging.getLogger(__name__)

LOCK_TRUEFALSE_CMDS = "true_false"
LOCK_OPENCLOSE_CMDS = "open_close"
LOCK_ONOFF_CMDS = "on_off"

DEFAULT_LOCK_COMMANDS_SET = LOCK_TRUEFALSE_CMDS


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_LOCK_COMMANDS_SET): vol.In(
            [LOCK_TRUEFALSE_CMDS, LOCK_OPENCLOSE_CMDS, LOCK_ONOFF_CMDS]
        ),
    }


class LocaltuyaLock(LocalTuyaEntity, LockEntity):
    """Tuya Lock device."""

    def __init__(self, device, config_entry, switchid, **kwargs):
        """Initialize a new LocaltuyaLock."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        commands_set = DEFAULT_LOCK_COMMANDS_SET
        if self.has_config(CONF_LOCK_COMMANDS_SET):
            commands_set = self._config[CONF_LOCK_COMMANDS_SET]
        self._open_cmd = commands_set.split("_")[0]
        self._close_cmd = commands_set.split("_")[1]
        if commands_set == LOCK_TRUEFALSE_CMDS:
            self._open_cmd = True
            self._close_cmd = False
        self._state = self._open_cmd
        print("Initialized lock [{}]".format(self.name))

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN
        return supported_features

    @property
    def is_locked(self):
        """Always return false."""
        return self._state == self._close_cmd

    async def async_lock(self, **kwargs):
        """Lock the smart lock."""
        self.debug("Launching command %s to lock ", self._close_cmd)
        await self._device.set_dp(self._close_cmd, self._dp_id)

    async def async_unlock(self, **kwargs):
        """Unlock the smart lock."""
        self.debug("Launching command %s to unlock ", self._open_cmd)
        await self._device.set_dp(self._open_cmd, self._dp_id)

    async def async_open(self, **kwargs):
        """Open the door."""
        self.debug("Launching command %s to unlock ", self._open_cmd)
        await self._device.set_dp(self._open_cmd, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)
        self.debug("Lock status update: %r", self._state)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaLock, flow_schema)
