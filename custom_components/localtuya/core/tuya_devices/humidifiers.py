"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory
from homeassistant.components.humidifier import HumidifierDeviceClass

HUMIDIFIERS: dict[LocalTuyaEntity] = {
    # Dehumidifier
    # https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
    "cs": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH_SPRAY, DPCode.SWITCH),
            # dpcode=(DPCode.SWITCH, DPCode.SWITCH_SPRAY),
            current_humidity_dp=DPCode.HUMIDITY_INDOOR,
            set_humidity_dp=DPCode.DEHUMIDITY_SET_VALUE,
            device_class=HumidifierDeviceClass.DEHUMIDIFIER,
        )
    ),
    # Humidifier
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": (
        LocalTuyaEntity(
            id=(DPCode.SWITCH_SPRAY, DPCode.SWITCH),
            # dpcode=(DPCode.SWITCH, DPCode.SWITCH_SPRAY),
            current_humidity_dp=DPCode.HUMIDITY_CURRENT,
            set_humidity_dp=DPCode.HUMIDITY_SET,
            device_class=HumidifierDeviceClass.HUMIDIFIER,
        )
    ),
}
