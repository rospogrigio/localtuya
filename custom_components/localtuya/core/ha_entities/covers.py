"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory
from homeassistant.components.cover import CoverDeviceClass

# from const.py this is temporarily.
CONF_COMMANDS_SET = "commands_set"
CONF_POSITIONING_MODE = "positioning_mode"
CONF_CURRENT_POSITION_DP = "current_position_dp"
CONF_SET_POSITION_DP = "set_position_dp"
CONF_POSITION_INVERTED = "position_inverted"
CONF_SPAN_TIME = "span_time"


def localtuya_cover(cmd_set, position_mode=None, inverted=False, timed=25):
    """Define localtuya cover configs"""
    data = {
        CONF_COMMANDS_SET: cmd_set,
        CONF_POSITIONING_MODE: position_mode,
        CONF_POSITION_INVERTED: inverted,
        CONF_SPAN_TIME: timed,
    }
    return data


COVERS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Curtain
    # Note: Multiple curtains isn't documented
    # https://developer.tuya.com/en/docs/iot/categorycl?id=Kaiuz1hnpo7df
    "cl": (
        LocalTuyaEntity(
            id=DPCode.CONTROL,
            name="Curtain",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_state=DPCode.SITUATION_SET,
            current_position_dp=(DPCode.PERCENT_STATE, DPCode.PERCENT_CONTROL),
            set_position_dp=DPCode.PERCENT_CONTROL,
        ),
        LocalTuyaEntity(
            id=DPCode.CONTROL_2,
            name="Curtain 2",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=(DPCode.PERCENT_STATE_2, DPCode.PERCENT_CONTROL_2),
            set_position_dp=DPCode.PERCENT_CONTROL_2,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        LocalTuyaEntity(
            id=DPCode.CONTROL_3,
            name="Curtain 3",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=(DPCode.PERCENT_STATE_3, DPCode.PERCENT_CONTROL_3),
            set_position_dp=DPCode.PERCENT_CONTROL_3,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        LocalTuyaEntity(
            id=DPCode.CONTROL_4,
            name="Curtain 4",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=(DPCode.PERCENT_STATE_4, DPCode.PERCENT_CONTROL_4),
            set_position_dp=DPCode.PERCENT_CONTROL_4,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        LocalTuyaEntity(
            id=DPCode.MACH_OPERATE,
            name="Curtain",
            custom_configs=localtuya_cover("fz_zz_stop", "position"),
            current_position_dp=DPCode.POSITION,
            set_position_dp=DPCode.POSITION,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        # switch_1 is an undocumented code that behaves identically to control
        # It is used by the Kogan Smart Blinds Driver
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Blind",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=DPCode.PERCENT_CONTROL,
            set_position_dp=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.BLIND,
        ),
    ),
    # Garage Door Opener
    # https://developer.tuya.com/en/docs/iot/categoryckmkzq?id=Kaiuz0ipcboee
    "ckmkzq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="Door",
            custom_configs=localtuya_cover("open_close_stop", "none", True),
            current_position_dp=DPCode.DOORCONTACT_STATE,
            device_class=CoverDeviceClass.GARAGE,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_2,
            name="Door 2",
            custom_configs=localtuya_cover("open_close_stop", "none", True),
            current_position_dp=DPCode.DOORCONTACT_STATE_2,
            device_class=CoverDeviceClass.GARAGE,
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_3,
            name="Door 3",
            custom_configs=localtuya_cover("open_close_stop", "none", True),
            current_position_dp=DPCode.DOORCONTACT_STATE_3,
            device_class=CoverDeviceClass.GARAGE,
        ),
    ),
    # Curtain Switch
    # https://developer.tuya.com/en/docs/iot/category-clkg?id=Kaiuz0gitil39
    "clkg": (
        LocalTuyaEntity(
            id=DPCode.CONTROL,
            name="Curtain",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=DPCode.PERCENT_CONTROL,
            set_position_dp=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.CURTAIN,
        ),
        LocalTuyaEntity(
            id=DPCode.CONTROL_2,
            name="Curtain 2",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=DPCode.PERCENT_CONTROL_2,
            set_position_dp=DPCode.PERCENT_CONTROL_2,
            device_class=CoverDeviceClass.CURTAIN,
        ),
    ),
    # Curtain Robot
    # Note: Not documented
    "jdcljqr": (
        LocalTuyaEntity(
            id=DPCode.CONTROL,
            name="Curtain",
            custom_configs=localtuya_cover("open_close_stop", "position"),
            current_position_dp=DPCode.PERCENT_STATE,
            set_position_dp=DPCode.PERCENT_CONTROL,
            device_class=CoverDeviceClass.CURTAIN,
        ),
    ),
}
