"""Platform to present any Tuya DP as a Lock."""

import logging
from functools import partial
from typing import Any
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.lock import DOMAIN, LockEntity
from .entity import LocalTuyaEntity, async_setup_entry

from .const import CONF_JAMMED_DP, CONF_LOCK_STATE_DP

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_LOCK_STATE_DP): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_JAMMED_DP): col_to_select(dps, is_dps=True),
    }


class LocalTuyaLock(LocalTuyaEntity, LockEntity):
    """Representation of a Tuya Lock."""

    def __init__(
        self,
        device,
        config_entry,
        Lockid,
        **kwargs,
    ):
        """Initialize the Tuya Lock."""
        super().__init__(device, config_entry, Lockid, _LOGGER, **kwargs)
        self._state = None

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self._device.set_dp(True, self._dp_id)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self._device.set_dp(False, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        state = self.dp_value(self._dp_id)
        if (lock_state := self.dp_value(CONF_LOCK_STATE_DP)) or lock_state is not None:
            state = lock_state

        self._attr_is_locked = state in (False, "closed", "close", None)

        if jammed := self.dp_value(CONF_JAMMED_DP, False):
            self._attr_is_jammed = jammed

    # No need to restore state for a Lock
    async def restore_state_when_connected(self):
        """Do nothing for a Lock."""
        return


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaLock, flow_schema)
