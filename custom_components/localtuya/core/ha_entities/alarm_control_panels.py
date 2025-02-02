"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CLOUD_VALUE
from ...const import CONF_ALARM_SUPPORTED_STATES
from homeassistant.const import (
    STATE_ALARM_DISARMED,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_ARMED_VACATION,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_PENDING,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMING,
    STATE_ALARM_TRIGGERED,
)

MAP_ALARM_STATES = {
    "disarmed": STATE_ALARM_DISARMED,
    "arm": STATE_ALARM_ARMED_AWAY,
    "home": STATE_ALARM_ARMED_HOME,
    "sos": STATE_ALARM_TRIGGERED,
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
                    STATE_ALARM_DISARMED: "disarmed",
                    STATE_ALARM_ARMED_AWAY: "arm",
                    STATE_ALARM_ARMED_HOME: "home",
                    STATE_ALARM_TRIGGERED: "sos",
                }
            ),
        ),
    ),
}
