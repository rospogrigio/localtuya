"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import (
    DPCode,
    LocalTuyaEntity,
    CONF_DEVICE_CLASS,
    EntityCategory,
    CLOUD_VALUE,
)
from homeassistant.components.fan import DIRECTION_FORWARD, DIRECTION_REVERSE

# from const.py this is temporarily
CONF_FAN_SPEED_CONTROL = "fan_speed_control"
CONF_FAN_OSCILLATING_CONTROL = "fan_oscillating_control"
CONF_FAN_DIRECTION = "fan_direction"

CONF_FAN_SPEED_MIN = "fan_speed_min"
CONF_FAN_SPEED_MAX = "fan_speed_max"
CONF_FAN_DIRECTION_FWD = "fan_direction_forward"
CONF_FAN_DIRECTION_REV = "fan_direction_reverse"
CONF_FAN_DPS_TYPE = "fan_dps_type"
CONF_FAN_ORDERED_LIST = "fan_speed_ordered_list"

FAN_SPEED_DP = (
    DPCode.FAN_SPEED_PERCENT,
    DPCode.FAN_SPEED,
    DPCode.SPEED,
    DPCode.FAN_SPEED_ENUM,
)

FANS_OSCILLATING = (DPCode.SWITCH_HORIZONTAL, DPCode.SWITCH_VERTICAL)


def localtuya_fan(fwd, rev, min_speed, max_speed, order, dp_type):
    """Define localtuya fan configs"""
    data = {
        CONF_FAN_DIRECTION_FWD: fwd,
        CONF_FAN_DIRECTION_REV: rev,
        CONF_FAN_SPEED_MIN: CLOUD_VALUE(min_speed, CONF_FAN_SPEED_CONTROL, "min"),
        CONF_FAN_SPEED_MAX: CLOUD_VALUE(max_speed, CONF_FAN_SPEED_CONTROL, "max"),
        CONF_FAN_ORDERED_LIST: CLOUD_VALUE(order, CONF_FAN_SPEED_CONTROL, "range", str),
        CONF_FAN_DPS_TYPE: dp_type,
    }
    return data


FANS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Fan
    "fs": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH_FAN, DPCode.FAN_SWITCH, DPCode.SWITCH),
            name="Fan",
            icon="mdi:fan",
            fan_speed_control=FAN_SPEED_DP,
            fan_direction=DPCode.FAN_DIRECTION,
            fan_oscillating_control=FANS_OSCILLATING,
            custom_configs=localtuya_fan(
                DIRECTION_FORWARD, DIRECTION_REVERSE, 1, 100, "disabled", "int"
            ),
        ),
    ),
    # Normal switch with fan controller.
    "tdq": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH_FAN, DPCode.FAN_SWITCH),
            name="Fan",
            icon="mdi:fan",
            fan_speed_control=FAN_SPEED_DP,
            fan_direction=DPCode.FAN_DIRECTION,
            fan_oscillating_control=FANS_OSCILLATING,
            custom_configs=localtuya_fan(
                DIRECTION_FORWARD, DIRECTION_REVERSE, 1, 100, "disabled", "int"
            ),
        ),
    ),
}
# Fan with Light
FANS["fsd"] = FANS["fs"]
# Fan wall switch
FANS["fskg"] = FANS["fs"]
# Air Purifier
FANS["kj"] = FANS["fs"]
