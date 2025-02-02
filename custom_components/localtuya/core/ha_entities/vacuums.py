"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CLOUD_VALUE

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
DEFAULT_RETURNING_STATUS = "docking,to_charge,goto_charge"
DEFAULT_DOCKED_STATUS = "charging,chargecompleted,charge_done"
DEFAULT_MODES = "smart,wall_follow,spiral,single"
DEFAULT_FAN_SPEEDS = "low,normal,high"
DEFAULT_PAUSED_STATE = "paused"
DEFAULT_RETURN_MODE = "chargego"
DEFAULT_STOP_STATUS = "standby"


def localtuya_vaccuums(
    modes: str = None,
    returning_status_value: str = None,
    return_mode: str = None,
    fan_speeds: str = None,
    paused_state: str = None,
    stop_status: str = None,
    idle_status_value: str = None,
    docked_status_value: str = None,
) -> dict:
    """Will return dict with the vacuum localtuya entity configs"""
    data = {
        CONF_MODES: CLOUD_VALUE(modes, CONF_MODE_DP, "range", str),
        CONF_IDLE_STATUS_VALUE: idle_status_value or DEFAULT_IDLE_STATUS,
        CONF_STOP_STATUS: stop_status or DEFAULT_STOP_STATUS,
        CONF_PAUSED_STATE: paused_state or DEFAULT_PAUSED_STATE,
        CONF_FAN_SPEEDS: CLOUD_VALUE(fan_speeds, CONF_FAN_SPEED_DP, "range", str),
        CONF_RETURN_MODE: return_mode or DEFAULT_RETURN_MODE,
        CONF_RETURNING_STATUS_VALUE: returning_status_value or DEFAULT_RETURNING_STATUS,
        CONF_DOCKED_STATUS_VALUE: docked_status_value or CONF_DOCKED_STATUS_VALUE,
    }

    return data


VACUUMS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.STATUS,
            icon="mdi:robot-vacuum",
            powergo_dp=(DPCode.POWER_GO, DPCode.POWER, DPCode.SWITCH),
            battery_dp=(
                DPCode.BATTERY_PERCENTAGE,
                DPCode.ELECTRICITY_LEFT,
                DPCode.RESIDUAL_ELECTRICITY,
            ),
            mode_dp=DPCode.MODE,
            fan_speed_dp=DPCode.SUCTION,
            pause_dp=DPCode.PAUSE,
            locate_dp=DPCode.SEEK,
            clean_time_dp=(
                DPCode.CLEAN_TIME,
                DPCode.TOTAL_CLEAN_AREA,
                DPCode.TOTAL_CLEAN_TIME,
            ),
            clean_area_dp=DPCode.CLEAN_AREA,
            clean_record_dp=DPCode.CLEAN_RECORD,
            fault_dp=DPCode.FAULT,
            custom_configs=localtuya_vaccuums(
                modes=DEFAULT_MODES,
                returning_status_value=DEFAULT_RETURNING_STATUS,
                return_mode=DEFAULT_RETURN_MODE,
                fan_speeds=DEFAULT_FAN_SPEEDS,
                paused_state=DEFAULT_PAUSED_STATE,
                stop_status=DEFAULT_STOP_STATUS,
                idle_status_value=DEFAULT_IDLE_STATUS,
                docked_status_value=DEFAULT_DOCKED_STATUS,
            ),
        ),
    ),
}
