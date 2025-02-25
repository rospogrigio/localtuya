"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from homeassistant.components.climate import (
    HVACMode,
    HVACAction,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
)
from homeassistant.const import CONF_TEMPERATURE_UNIT

from .base import DPCode, LocalTuyaEntity, CLOUD_VALUE
from ...const import (
    CONF_ECO_VALUE,
    CONF_HVAC_ACTION_SET,
    CONF_HVAC_MODE_SET,
    CONF_PRECISION,
    CONF_PRESET_SET,
    CONF_TARGET_PRECISION,
    CONF_TEMPERATURE_STEP,
    CONF_HVAC_ACTION_DP,
    CONF_HVAC_MODE_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_FAN_SPEED_LIST,
    CONF_FAN_SPEED_DP,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_PRESET_DP,
)


UNIT_C = "celsius"
UNIT_F = "fahrenheit"

FAN_SPEEDS_DEFAULT = "auto,low,middle,high"


def localtuya_climate(
    hvac_mode_set=None,
    temp_step=1,
    actions_set=None,
    echo_value=None,
    preset_set=None,
    fans_speeds=FAN_SPEEDS_DEFAULT,
    unit=None,
    min_temperature=7,
    max_temperature=35,
    values_precsion=0.1,
    target_precision=1,
) -> dict:
    """Create localtuya climate configs"""
    data = {}
    for key, conf in {
        CONF_HVAC_MODE_SET: CLOUD_VALUE(
            hvac_mode_set, CONF_HVAC_MODE_DP, "range", dict, MAP_CLIMATE_MODES, True
        ),
        CONF_MIN_TEMP: CLOUD_VALUE(
            min_temperature, CONF_TARGET_TEMPERATURE_DP, "min", scale=True
        ),
        CONF_MAX_TEMP: CLOUD_VALUE(
            max_temperature, CONF_TARGET_TEMPERATURE_DP, "max", scale=True
        ),
        CONF_TEMPERATURE_STEP: CLOUD_VALUE(
            str(temp_step), CONF_TARGET_TEMPERATURE_DP, "step", str, scale=True
        ),
        CONF_HVAC_ACTION_SET: CLOUD_VALUE(
            actions_set, CONF_HVAC_ACTION_DP, "range", dict, MAP_CLIMATE_ACTIONS, True
        ),
        CONF_FAN_SPEED_LIST: CLOUD_VALUE(fans_speeds, CONF_FAN_SPEED_DP, "range", str),
        CONF_ECO_VALUE: echo_value,
        CONF_PRESET_SET: CLOUD_VALUE(preset_set, CONF_PRESET_DP, "range", dict),
        CONF_TEMPERATURE_UNIT: unit,
        CONF_PRECISION: CLOUD_VALUE(
            str(values_precsion), CONF_CURRENT_TEMPERATURE_DP, "scale", str
        ),
        CONF_TARGET_PRECISION: CLOUD_VALUE(
            str(target_precision), CONF_TARGET_TEMPERATURE_DP, "scale", str
        ),
    }.items():
        if conf:
            data.update({key: conf})

    return data


# Map used for cloud value obtain.
MAP_CLIMATE_MODES = {
    "off": HVACMode.OFF,
    "auto": HVACMode.AUTO,
    "cold": HVACMode.COOL,
    "freeze": HVACMode.COOL,
    "cooling": HVACMode.COOL,
    "hot": HVACMode.HEAT,
    "heating": HVACMode.HEAT,
    "manual": HVACMode.HEAT_COOL,
    "wet": HVACMode.DRY,
    "dehum": HVACMode.DRY,
    "wind": HVACMode.FAN_ONLY,
    "fan": HVACMode.FAN_ONLY,
    "off": HVACMode.OFF,
    "0": HVACMode.COOL,
    "1": HVACMode.HEAT,
    "2": HVACMode.FAN_ONLY,
}
MAP_CLIMATE_ACTIONS = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "warming": HVACAction.IDLE,
    "opened": HVACAction.HEATING,
    "closed": HVACAction.IDLE,
}

CLIMATES: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Air conditioner
    # https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    "kt": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            target_temperature_dp=(DPCode.TEMP_SET, DPCode.TEMP_SET_F),
            current_temperature_dp=(
                DPCode.TEMP_CURRENT,
                DPCode.TEMP_CURRENT_F,
                DPCode.TEMPCURRENT,
            ),
            hvac_mode_dp=(DPCode.SYSTEMMODE, DPCode.MODE),
            hvac_action_dp=(DPCode.WORK_MODE, DPCode.WORK_STATUS, DPCode.WORK_STATE),
            preset_dp=DPCode.MODE,
            fan_speed_dp=(DPCode.FAN_SPEED_ENUM, DPCode.WINDSPEED),
            custom_configs=localtuya_climate(
                hvac_mode_set={
                    HVACMode.AUTO: "auto",
                    HVACMode.COOL: "cold",
                    HVACMode.HEAT: "hot",
                    HVACMode.DRY: "wet",
                },
                preset_set={},
                temp_step=1,
                actions_set={
                    HVACAction.HEATING: "heating",
                    HVACAction.COOLING: "cooling",
                },
                unit=UNIT_C,
                values_precsion=0.1,
                target_precision=0.1,
            ),
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46epy4j82
    "qn": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            target_temperature_dp=(DPCode.TEMP_SET, DPCode.TEMP_SET_F),
            current_temperature_dp=(DPCode.TEMP_CURRENT, DPCode.TEMP_CURRENT_F),
            hvac_mode_dp=DPCode.SWITCH,
            hvac_action_dp=(DPCode.WORK_STATE, DPCode.WORK_MODE, DPCode.WORK_STATUS),
            preset_dp=DPCode.MODE,
            fan_speed_dp=(DPCode.FAN_SPEED_ENUM, DPCode.WINDSPEED),
            custom_configs=localtuya_climate(
                hvac_mode_set={
                    HVACMode.OFF: False,
                    HVACMode.HEAT: True,
                },
                temp_step=1,
                actions_set={
                    HVACAction.HEATING: True,
                    HVACAction.IDLE: False,
                },
                values_precsion=0.1,
                target_precision=0.1,
                preset_set={},
            ),
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryrs?id=Kaiuz0nfferyx
    ## Converted to Water Heaters
    # "rs": (
    #     LocalTuyaEntity(
    #         id=DPCode.SWITCH,
    #         target_temperature_dp=(DPCode.TEMP_SET, DPCode.TEMP_SET_F),
    #         current_temperature_dp=(DPCode.TEMP_CURRENT, DPCode.TEMP_CURRENT_F),
    #         hvac_action_dp=(DPCode.WORK_STATE, DPCode.WORK_MODE, DPCode.WORK_STATUS),
    #         preset_dp=DPCode.MODE,
    #         fan_speed_dp=(DPCode.FAN_SPEED_ENUM, DPCode.WINDSPEED),
    #         custom_configs=localtuya_climate(
    #             hvac_mode_set={
    #                 HVACMode.OFF: "off",
    #                 HVACMode.HEAT: "hot",
    #             },
    #             temp_step=1,
    #             actions_set={
    #                 HVACAction.HEATING: "heating",
    #                 HVACAction.IDLE: "warming",
    #             },
    #             unit=UNIT_C,
    #             values_precsion=0.1,
    #             target_precision=0.1,
    #             preset_set={},
    #         ),
    #     ),
    # ),
    # Thermostat
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf45ld5l0t9
    "wk": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH, DPCode.MODE),
            target_temperature_dp=(DPCode.TEMP_SET, DPCode.TEMP_SET_F),
            current_temperature_dp=(
                DPCode.TEMP_CURRENT,
                DPCode.TEMP_CURRENT_F,
                DPCode.TEMPCURRENT,
            ),
            hvac_mode_dp=(DPCode.SYSTEMMODE, DPCode.SWITCH, DPCode.MODE),
            hvac_action_dp=(DPCode.WORK_STATE, DPCode.WORK_MODE, DPCode.WORK_STATUS),
            preset_dp=DPCode.MODE,
            fan_speed_dp=(DPCode.FAN_SPEED_ENUM, DPCode.WINDSPEED, DPCode.SPEED),
            custom_configs=localtuya_climate(
                hvac_mode_set={HVACMode.HEAT: True, HVACMode.OFF: False},
                temp_step=1,
                actions_set={
                    HVACAction.HEATING: True,
                    HVACAction.IDLE: False,
                },
                unit=UNIT_C,
                values_precsion=0.1,
                target_precision=0.1,
            ),
        ),
    ),
    # Thermostatic Radiator Valve
    # Not documented
    "wkf": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH, DPCode.MODE),
            target_temperature_dp=(DPCode.TEMP_SET, DPCode.TEMP_SET_F),
            current_temperature_dp=(
                DPCode.TEMP_CURRENT,
                DPCode.TEMP_CURRENT_F,
                DPCode.TEMPCURRENT,
            ),
            hvac_mode_dp=(DPCode.SYSTEMMODE, DPCode.MODE),
            hvac_action_dp=(DPCode.WORK_STATE, DPCode.WORK_MODE, DPCode.WORK_STATUS),
            preset_dp=DPCode.MODE,
            fan_speed_dp=(DPCode.FAN_SPEED_ENUM, DPCode.WINDSPEED, DPCode.SPEED),
            custom_configs=localtuya_climate(
                hvac_mode_set={
                    HVACMode.HEAT: "manual",
                    HVACMode.AUTO: "auto",
                },
                temp_step=1,
                actions_set={HVACAction.HEATING: "opened", HVACAction.IDLE: "closed"},
                unit=UNIT_C,
                values_precsion=0.1,
                target_precision=0.1,
            ),
        ),
    ),
}
