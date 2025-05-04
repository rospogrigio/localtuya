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
from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
)

CONF_HUMIDIFIER_SET_HUMIDITY_DP = "humidifier_set_humidity_dp"
CONF_HUMIDIFIER_CURRENT_HUMIDITY_DP = "humidifier_current_humidity_dp"
CONF_HUMIDIFIER_MODE_DP = "humidifier_mode_dp"
CONF_HUMIDIFIER_AVAILABLE_MODES = "humidifier_available_modes"


def localtuya_humidifier(modes):
    """Define localtuya fan configs"""

    data = {
        CONF_HUMIDIFIER_AVAILABLE_MODES: CLOUD_VALUE(
            modes, CONF_HUMIDIFIER_MODE_DP, "range", dict
        ),
        ATTR_MIN_HUMIDITY: CLOUD_VALUE(
            DEFAULT_MIN_HUMIDITY, CONF_HUMIDIFIER_SET_HUMIDITY_DP, "min"
        ),
        ATTR_MAX_HUMIDITY: CLOUD_VALUE(
            DEFAULT_MAX_HUMIDITY, CONF_HUMIDIFIER_SET_HUMIDITY_DP, "max"
        ),
    }
    return data


HUMIDIFIERS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
    "cs": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            humidifier_current_humidity_dp=DPCode.HUMIDITY_INDOOR,
            humidifier_set_humidity_dp=DPCode.DEHUMIDITY_SET_VALUE,
            humidifier_mode_dp=(DPCode.MODE, DPCode.WORK_MODE),
            custom_configs=localtuya_humidifier(
                {
                    "dehumidify": "Dehumidify",
                    "drying": "Drying",
                    "continuous": "Continuous",
                }
            ),
            device_class=HumidifierDeviceClass.DEHUMIDIFIER,
        ),
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH,
            humidifier_current_humidity_dp=DPCode.HUMIDITY_CURRENT,
            humidifier_set_humidity_dp=DPCode.HUMIDITY_SET,
            humidifier_mode_dp=(DPCode.MODE, DPCode.WORK_MODE),
            custom_configs=localtuya_humidifier(
                {
                    "large": "Large",
                    "middle": "Middle",
                    "small": "Small",
                }
            ),
            device_class=HumidifierDeviceClass.HUMIDIFIER,
        ),
    ),
}
