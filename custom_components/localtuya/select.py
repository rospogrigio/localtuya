"""Platform to locally control Tuya-based switch devices."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.select import DOMAIN, SelectEntity

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_SELECT_VALUES,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_SELECT_VALUES): vol.In(dps),
    }


class LocaltuyaSelect(LocalTuyaEntity, SelectEntity):
    """Representation of a Tuya select."""

    def __init__(
            self,
            device,
            config_entry,
            select_id,
            **kwargs,
    ):
        """Initialize the Tuya switch."""
        super().__init__(device, config_entry, select_id, _LOGGER, **kwargs)
        self._state = None
        self._values = None
        print("Initialized select [{}]".format(self.name))

    @property
    def current_option(self):
        """Return currently selected option"""
        return self._state

    @property
    def options(self):
        """List of options"""
        if self._values is not None:
            return self._values

        select_values = self._config.get(CONF_SELECT_VALUES)
        if select_values is None:
            self._values = ("None")
        else:
            self._values = str(select_values).split("|")
        self.debug("Computed select values as %s", self._values)
        return self._values

    async def async_select_option(self, option: str) -> None:
        """Sets value to the device"""
        self.debug("Selecting value: %s", option)
        await self._device.set_dp(option, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        self._state = self.dps(self._dp_id)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSelect, flow_schema)
