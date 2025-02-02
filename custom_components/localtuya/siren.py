"""Platform to present any Tuya DP as a siren."""

import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.siren import DOMAIN, SirenEntity, SirenEntityFeature

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_STATE_ON

_LOGGER = logging.getLogger(__name__)

# CONF_STATE_MAP = ["True and False", "ON and OFF"]


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_STATE_ON, default="true"): str,
        # vol.Required(CONF_STATE_OFF, default="False"): str,
    }


class LocalTuyaSiren(LocalTuyaEntity, SirenEntity):
    """Representation of a Tuya siren."""

    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF

    def __init__(
        self,
        device,
        config_entry,
        sirenid,
        **kwargs,
    ):
        """Initialize the Tuya siren."""
        super().__init__(device, config_entry, sirenid, _LOGGER, **kwargs)
        self._is_on = False

    @property
    def is_on(self):
        """Return siren state."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn Tuya siren on."""
        await self._device.set_dp(True, self._dp_id)

    async def async_turn_off(self, **kwargs):
        """Turn Tuya siren off."""
        await self._device.set_dp(False, self._dp_id)

    # No need to restore state for a siren
    async def restore_state_when_connected(self):
        """Do nothing for a siren."""
        return

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

        state = str(self.dp_value(self._dp_id)).lower()
        if state == self._config[CONF_STATE_ON].lower() or state == "true":
            self._is_on = True
        else:
            self._is_on = False


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaSiren, flow_schema)
