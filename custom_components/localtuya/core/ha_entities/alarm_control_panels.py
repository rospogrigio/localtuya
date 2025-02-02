"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CLOUD_VALUE
from ...const import CONF_ALARM_SUPPORTED_STATES
from homeassistant.components.alarm_control_panel import AlarmControlPanelState

MAP_ALARM_STATES = {
    "disarmed": AlarmControlPanelState.DISARMED,
    "arm": AlarmControlPanelState.ARMED_AWAY,
    "home": AlarmControlPanelState.ARMED_HOME,
    "sos": AlarmControlPanelState.TRIGGERED,
}


def localtuya_alarm(states: dict):
    """Generate localtuya alarm configs"""
    data = {
        CONF_ALARM_SUPPORTED_STATES: CLOUD_VALUE(
            states, "id", "range", dict, MAP_ALARM_STATES, True
        ),
    }
    return data


# All descriptions can be found here:
# https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
ALARMS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Alarm Host
    # https://developer.tuya.com/en/docs/iot/categorymal?id=Kaiuz33clqxaf
    "mal": (
        LocalTuyaEntity(
            id=DPCode.MASTER_MODE,
            custom_configs=localtuya_alarm(
                {
                    AlarmControlPanelState.DISARMED: "disarmed",
                    AlarmControlPanelState.ARMED_AWAY: "arm",
                    AlarmControlPanelState.ARMED_HOME: "home",
                    AlarmControlPanelState.TRIGGERED: "sos",
                }
            ),
        ),
    ),
}
