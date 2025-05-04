"""Platform to locally control Tuya-based switch devices."""

import logging
from functools import partial
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.switch import (
    DOMAIN,
    SwitchEntity,
    DEVICE_CLASSES_SCHEMA,
    SwitchDeviceClass,
)
from homeassistant.const import CONF_DEVICE_CLASS

from .entity import LocalTuyaEntity, async_setup_entry
from .const import (
    ATTR_CURRENT,
    ATTR_CURRENT_CONSUMPTION,
    ATTR_STATE,
    ATTR_VOLTAGE,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_DEFAULT_VALUE,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
    CONF_VOLTAGE,
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_CURRENT): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_CURRENT_CONSUMPTION): col_to_select(dps, is_dps=True),
        vol.Optional(CONF_VOLTAGE): col_to_select(dps, is_dps=True),
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
        vol.Required(CONF_PASSIVE_ENTITY): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
        vol.Optional(CONF_DEVICE_CLASS): col_to_select(
            [sc.value for sc in SwitchDeviceClass]
        ),
    }


class LocalTuyaSwitch(LocalTuyaEntity, SwitchEntity):
    """Representation of a Tuya switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        device,
        config_entry,
        switchid,
        **kwargs,
    ):
        """Initialize the Tuya switch."""
        super().__init__(device, config_entry, switchid, _LOGGER, **kwargs)
        self._state = None

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return device state attributes."""
        attrs = {}
        if self.has_config(CONF_CURRENT):
            attrs[ATTR_CURRENT] = self.dp_value(self._config[CONF_CURRENT])
        if self.has_config(CONF_CURRENT_CONSUMPTION):
            val_cc = self.dp_value(self._config[CONF_CURRENT_CONSUMPTION])
            attrs[ATTR_CURRENT_CONSUMPTION] = None if val_cc is None else val_cc / 10
        if self.has_config(CONF_VOLTAGE):
            val_vol = self.dp_value(self._config[CONF_VOLTAGE])
            attrs[ATTR_VOLTAGE] = None if val_vol is None else val_vol / 10

        # Store the state
        if self._state is not None:
            attrs[ATTR_STATE] = self._state
        elif self._last_state is not None:
            attrs[ATTR_STATE] = self._last_state
        return attrs

    async def async_turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        await self._device.set_dp(True, self._dp_id)

    async def async_turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        await self._device.set_dp(False, self._dp_id)

    # Default value is the "OFF" state
    def entity_default_value(self):
        """Return False as the default value for this entity type."""
        return False


async_setup_entry = partial(async_setup_entry, DOMAIN, LocalTuyaSwitch, flow_schema)
