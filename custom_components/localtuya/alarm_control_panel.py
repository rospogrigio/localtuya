"""Platform to present any Tuya DP as a Alarm."""

from enum import StrEnum
import logging
from functools import partial
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.helpers import selector
from homeassistant.components.alarm_control_panel import (
    DOMAIN,
    AlarmControlPanelEntity,
    CodeFormat,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_ALARM_SUPPORTED_STATES

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 2


class TuyaMode(StrEnum):
    DISARMED = "disarmed"
    ARM = "arm"
    HOME = "home"
    SOS = "sos"


DEFAULT_SUPPORTED_MODES = {
    AlarmControlPanelState.DISARMED: TuyaMode.DISARMED,
    AlarmControlPanelState.ARMED_AWAY: TuyaMode.ARM,
    AlarmControlPanelState.ARMED_HOME: TuyaMode.HOME,
    AlarmControlPanelState.TRIGGERED: TuyaMode.SOS,
}


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(
            CONF_ALARM_SUPPORTED_STATES, default=DEFAULT_SUPPORTED_MODES
        ): selector.ObjectSelector(),
    }


class LocalTuyaAlarmControlPanel(LocalTuyaEntity, AlarmControlPanelEntity):
    """Representation of a Tuya Alarm."""

    _supported_modes = {}

    def __init__(
        self,
        device,
        config_entry,
        dpid,
        **kwargs,
    ):
        """Initialize the Tuya Alarm."""
        super().__init__(device, config_entry, dpid, _LOGGER, **kwargs)
        self._state = None
        self._changed_by = None

        # supported modes
        if supported_modes := self._config.get(CONF_ALARM_SUPPORTED_STATES, {}):
            # Key is HA state and value is Tuya State.
            if AlarmControlPanelState.ARMED_AWAY in supported_modes:
                self._attr_supported_features |= AlarmControlPanelEntityFeature.ARM_HOME
            if AlarmControlPanelState.ARMED_HOME in supported_modes:
                self._attr_supported_features |= AlarmControlPanelEntityFeature.ARM_AWAY
            if AlarmControlPanelState.TRIGGERED in supported_modes:
                self._attr_supported_features |= AlarmControlPanelEntityFeature.TRIGGER

        self._state_ha_to_tuya: dict[str, str] = supported_modes
        self._state_tuya_to_ha: dict[str, str] = {
            v: k for k, v in supported_modes.items()
        }

    @property
    def state(self):
        """Return Alarm state."""
        return self._state_tuya_to_ha.get(self._state, None)

    @property
    def code_format(self) -> CodeFormat | None:
        """Code format or None if no code is required."""
        return None  # self._attr_code_format

    @property
    def changed_by(self) -> str | None:
        """Last change triggered by."""
        return None  # self._attr_changed_by

    @property
    def code_arm_required(self) -> bool:
        """Whether the code is required for arm actions."""
        return True  # self._attr_code_arm_required

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        state = self._state_ha_to_tuya.get(AlarmControlPanelState.DISARMED)
        await self._device.set_dp(state, self._dp_id)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        state = self._state_ha_to_tuya.get(AlarmControlPanelState.ARMED_HOME)
        await self._device.set_dp(state, self._dp_id)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        state = self._state_ha_to_tuya.get(AlarmControlPanelState.ARMED_AWAY)
        await self._device.set_dp(state, self._dp_id)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send alarm trigger command."""
        state = self._state_ha_to_tuya.get(AlarmControlPanelState.TRIGGERED)
        await self._device.set_dp(state, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        super().status_updated()

    # No need to restore state for a AlarmControlPanel
    async def restore_state_when_connected(self):
        """Do nothing for a AlarmControlPanel."""
        return


async_setup_entry = partial(
    async_setup_entry, DOMAIN, LocalTuyaAlarmControlPanel, flow_schema
)
