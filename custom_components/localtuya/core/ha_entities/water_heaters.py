"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from homeassistant.components.water_heater import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
)
from homeassistant.const import CONF_TEMPERATURE_UNIT

from .base import DPCode, LocalTuyaEntity, CLOUD_VALUE
from ...const import (
    CONF_TARGET_TEMPERATURE_LOW_DP,
    CONF_TARGET_TEMPERATURE_HIGH_DP,
    CONF_PRECISION,
    CONF_TARGET_PRECISION,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_MODES,
    CONF_MODE_DP,
)


UNIT_C = "celsius"
UNIT_F = "fahrenheit"


def localtuya_water_heater(
    modes={},
    unit=None,
    min_temperature=DEFAULT_MIN_TEMP,
    max_temperature=DEFAULT_MAX_TEMP,
    current_precsion=0.1,
    target_precision=1,
) -> dict:
    """Create localtuya climate configs"""
    data = {}
    for key, conf in {
        CONF_MODES: CLOUD_VALUE(modes, CONF_MODE_DP, "range", dict),
        CONF_MIN_TEMP: CLOUD_VALUE(
            min_temperature, CONF_TARGET_TEMPERATURE_DP, "min", scale=True
        ),
        CONF_MAX_TEMP: CLOUD_VALUE(
            max_temperature, CONF_TARGET_TEMPERATURE_DP, "max", scale=True
        ),
        CONF_TEMPERATURE_UNIT: unit,
        CONF_PRECISION: CLOUD_VALUE(
            str(current_precsion), CONF_CURRENT_TEMPERATURE_DP, "scale", str
        ),
        CONF_TARGET_PRECISION: CLOUD_VALUE(
            str(target_precision), CONF_TARGET_TEMPERATURE_DP, "scale", str
        ),
    }.items():
        if conf is not None:
            data.update({key: conf})

    return data


WATER_HEATERS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Water Heater
    # https://developer.tuya.com/en/docs/iot/categoryrs?id=Kaiuz0nfferyx
    "rs": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            target_temperature_dp=(DPCode.TEMP_SET, DPCode.TEMP_SET_F),
            current_temperature_dp=(DPCode.TEMP_CURRENT, DPCode.TEMP_CURRENT_F),
            target_temperature_low_dp=(DPCode.TEMP_LOW, DPCode.LOWER_TEMP),
            target_temperature_high_dp=(DPCode.TEMP_UP, DPCode.UPPER_TEMP),
            mode_dp=DPCode.MODE,
            fan_speed_dp=(DPCode.FAN_SPEED_ENUM, DPCode.WINDSPEED),
            custom_configs=localtuya_water_heater(
                current_precsion=0.1, target_precision=0.1
            ),
        ),
    ),
}
