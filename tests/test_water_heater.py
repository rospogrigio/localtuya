"""Test for localtuya."""

from . import *
from custom_components.localtuya.water_heater import (
    LocalTuyaWaterHeater,
    DOMAIN as PLATFORM_DOMAIN,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_TARGET_TEMPERATURE_LOW_DP,
    CONF_TARGET_TEMPERATURE_HIGH_DP,
    CONF_MODES,
    CONF_MODE_DP,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "friendly_name": "Water Heater",
                "id": "1",
                "target_temperature_dp": "2",
                "target_temperature_low_dp": "2",
                "target_temperature_high_dp": "3",
                "current_temperature_dp": "4",
                "mode_dp": "5",
                "modes": {
                    "eheat": "Heating",
                    "bcool": "Cooling",
                    "auto": "Auto",
                },
                "precision": "1",
                "target_precision": "1",
                "is_passive_entity": False,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {
    "1": True,
    "2": 20,
    "3": 25,
    "4": 22,
    "5": "eheat",
}


async def test_water_heater():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaWaterHeater)
    entities: list[LocalTuyaWaterHeater] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaWaterHeater

    device.status_updated(DPS_STATUS)
    entity_1_cfg = CONFIG[DEVICE_NAME]["entities"][0]

    assert entity_1.state == entity_1_cfg[CONF_MODES].get(
        DPS_STATUS.get(entity_1_cfg[CONF_MODE_DP]), False
    )
    assert entity_1.target_temperature == DPS_STATUS.get(
        entity_1_cfg[CONF_TARGET_TEMPERATURE_DP], False
    )
    assert entity_1.target_temperature_low == DPS_STATUS.get(
        entity_1_cfg[CONF_TARGET_TEMPERATURE_LOW_DP], False
    )
    assert entity_1.target_temperature_high == DPS_STATUS.get(
        entity_1_cfg[CONF_TARGET_TEMPERATURE_HIGH_DP], False
    )
    assert entity_1.current_temperature == DPS_STATUS.get(
        entity_1_cfg[CONF_CURRENT_TEMPERATURE_DP], False
    )
