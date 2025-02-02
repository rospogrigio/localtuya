"""Test for localtuya."""

from . import *
from custom_components.localtuya.climate import (
    LocalTuyaClimate,
    HVACAction,
    HVACMode,
    DOMAIN as PLATFORM_DOMAIN,
)

FAN_SPEED_LIST = ["auto", "low", "middle", "high"]
CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "friendly_name": "Terrace Floor",
                "entity_category": "None",
                "target_temperature_dp": "16",
                "current_temperature_dp": "24",
                "temperature_step": "1",
                "min_temperature": 7.0,
                "max_temperature": 35.0,
                "precision": "1",
                "target_precision": "1",
                "hvac_mode_dp": "2",
                "hvac_mode_set": {
                    "auto": "program",
                    "heat": "manual",
                    "cool": "COLD",
                },
                "hvac_action_dp": "100",
                "hvac_action_set": {
                    "heating": True,
                    "idle": False,
                },
                "preset_dp": "5",
                "preset_set": {"holiday": "Holiday Friendly Name"},
                "fan_speed_dp": "6",
                "fan_speed_list": ",".join(FAN_SPEED_LIST),
                "temperature_unit": "fahrenheit/celsius",
                "id": "1",
                "eco_dp": "101",
                "eco_value": "eco_on",
                "platform": "climate",
                "icon": "",
                "heuristic_action": False,
            }
        ],
    }
}

DPS_STATUS = {
    "1": True,
    "2": "COLD",
    "5": "holiday",
    "6": "middle",
    "16": 68,  # F
    "24": 24,  # c
    "100": False,
    "101": "ECO_NOT",
}


async def test_climate():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaClimate)
    entities: list[LocalTuyaClimate] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaClimate

    assert entity_1._is_on == None

    status = {**DPS_STATUS, **{"1": False}}
    device.status_updated(status)
    assert type(entity_1._state_on) is bool

    assert entity_1._is_on == False
    assert entity_1.hvac_action == HVACAction.OFF
    assert entity_1.hvac_mode == HVACMode.OFF

    device.status_updated(DPS_STATUS)
    assert entity_1._is_on == True
    assert entity_1.hvac_action == HVACAction.IDLE
    assert entity_1.hvac_mode == HVACMode.COOL
    assert entity_1.fan_modes == FAN_SPEED_LIST
    assert entity_1.preset_mode == "Holiday Friendly Name"
    assert entity_1.current_temperature == 24
    assert entity_1.target_temperature == 20  # f to c
    assert entity_1.fan_mode == "middle"

    # Eco Preset
    device.status_updated({**DPS_STATUS, **{"101": "eco_on"}})
    assert entity_1.preset_mode == "eco"

    # heuristic_action
    entity_1._conf_hvac_action_dp = None
    status = {**DPS_STATUS, **{"2": "manual", "24": 18.9}}
    device.status_updated(status)
    assert entity_1.hvac_action == HVACAction.HEATING
    status = {**DPS_STATUS, **{"2": "manual", "24": 21.1}}
    device.status_updated(status)
    assert entity_1.hvac_action == HVACAction.IDLE

    # String DP ID
    status = {**DPS_STATUS, **{"1": "OFF"}}
    device.status_updated(status)
    assert not entity_1._is_on
    assert type(entity_1._state_on) is str

    # Integer DP ID
    status = {**DPS_STATUS, **{"1": 1}}
    device.status_updated(status)
    assert entity_1._is_on
    assert type(entity_1._state_on) is int
