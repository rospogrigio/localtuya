"""Platform to locally control Tuya-based button devices."""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.button import DOMAIN, ButtonEntity

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_PASSIVE_ENTITY

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        # vol.Required(CONF_PASSIVE_ENTITY): bool,
    }


class LocalTuyaButton(LocalTuyaEntity, ButtonEntity):
    """Representation of a Tuya button."""

    def __init__(
        self,
        device,
        config_entry,
        buttonid,
        **kwargs,
    ):
        """Initialize the Tuya button."""
        super().__init__(device, config_entry, buttonid, _LOGGER, **kwargs)
        self._state = None

    async def async_press(self):
        """Press the button."""
        await self._device.set_dp(True, self._dp_id)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaButton, flow_schema)
