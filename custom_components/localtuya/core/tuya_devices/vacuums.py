"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory

CONF_POWERGO_DP = "powergo_dp"
CONF_IDLE_STATUS_VALUE = "idle_status_value"
CONF_RETURNING_STATUS_VALUE = "returning_status_value"
CONF_DOCKED_STATUS_VALUE = "docked_status_value"
CONF_BATTERY_DP = "battery_dp"
CONF_MODE_DP = "mode_dp"
CONF_MODES = "modes"
CONF_FAN_SPEED_DP = "fan_speed_dp"
CONF_FAN_SPEEDS = "fan_speeds"
CONF_CLEAN_TIME_DP = "clean_time_dp"
CONF_CLEAN_AREA_DP = "clean_area_dp"
CONF_CLEAN_RECORD_DP = "clean_record_dp"
CONF_LOCATE_DP = "locate_dp"
CONF_FAULT_DP = "fault_dp"
CONF_PAUSED_STATE = "paused_state"
CONF_RETURN_MODE = "return_mode"
CONF_STOP_STATUS = "stop_status"

DEFAULT_IDLE_STATUS = "standby,sleep"
DEFAULT_RETURNING_STATUS = "docking"
DEFAULT_DOCKED_STATUS = "charging,chargecompleted"
DEFAULT_MODES = "smart,wall_follow,spiral,single"
DEFAULT_FAN_SPEEDS = "low,normal,high"
DEFAULT_PAUSED_STATE = "paused"
DEFAULT_RETURN_MODE = "chargego"
DEFAULT_STOP_STATUS = "standby"


DEFAULT_VALUES = {
    CONF_IDLE_STATUS_VALUE: DEFAULT_IDLE_STATUS,
    CONF_DOCKED_STATUS_VALUE: CONF_DOCKED_STATUS_VALUE,
    CONF_RETURNING_STATUS_VALUE: DEFAULT_RETURNING_STATUS,
    CONF_MODES: DEFAULT_MODES,
    CONF_RETURN_MODE: DEFAULT_RETURN_MODE,
    CONF_FAN_SPEEDS: DEFAULT_FAN_SPEEDS,
    CONF_PAUSED_STATE: DEFAULT_PAUSED_STATE,
    CONF_STOP_STATUS: DEFAULT_STOP_STATUS,
}


VACUUMS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH, DPCode.POWER),
            icon="mdi:robot-vacuum",
            powergo_dp=DPCode.POWER_GO,
            battery_dp=(DPCode.BATTERY_PERCENTAGE, DPCode.ELECTRICITY_LEFT),
            mode_dp=DPCode.MODE,
            clean_time_dp=(DPCode.TOTAL_CLEAN_AREA, DPCode.TOTAL_CLEAN_TIME),
            clean_area_dp=DPCode.CLEAN_AREA,
            clean_record_dp=DPCode.CLEAN_RECORD,
        ),
    ),
}
