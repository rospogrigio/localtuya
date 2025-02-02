"""Test for localtuya."""

from . import *
from custom_components.localtuya.vacuum import (
    LocalTuyaVacuum,
    DOMAIN as PLATFORM_DOMAIN,
    VacuumActivity,
    CONF_MODE_DP,
    CONF_PAUSE_DP,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "powergo_dp": "2",
                "idle_status_value": "standby,sleep",
                "docked_status_value": "charging,chargecompleted,charge_done",
                "returning_status_value": "docking,to_charge,goto_charge",
                "paused_state": "paused",
                "stop_status": "standby",
                "pause_dp": "101",
                "battery_dp": "6",
                "mode_dp": "3",
                "modes": "smart,zone,pose,part,chargego,wallfollow,selectroom",
                "return_mode": "chargego",
                "fan_speed_dp": "14",
                "fan_speeds": "strong,normal,quiet",
                "clean_time_dp": "17",
                "clean_area_dp": "16",
                "clean_record_dp": "19",
                "locate_dp": "13",
                "fault_dp": "18",
                "friendly_name": "",
                "id": "5",
                "platform": PLATFORM_DOMAIN,
                "icon": "mdi:robot-vacuum",
            }
        ],
    }
}

DPS_STATUS = {
    "2": True,  # powergo_dp
    "3": "smart",  # mode_dp
    "5": "cleaning",  # id - state
    "6": 45,  # battery_dp
    "13": False,  # locate_dp
    "14": "quiet",  # fan_speed_dp
    "16": 0,  # clean_area_dp
    "17": 0,  # clean_time_dp
    "18": 0,  # fault_dp
    "19": "",  # clean_record_dp
    "101": False,  # pause_dp
}


async def test_vacuum():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaVacuum)
    entities: list[LocalTuyaVacuum] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaVacuum

    entity_1_cfg = CONFIG[DEVICE_NAME]["entities"][0]

    status = DPS_STATUS.copy()
    device.status_updated(status)
    assert entity_1.state == VacuumActivity.CLEANING
    assert entity_1.battery_level == 45
    assert entity_1.fan_speed == "quiet"
    assert status[entity_1_cfg[CONF_MODE_DP]] in entity_1._modes_list

    device.status_updated({entity_1_cfg[CONF_PAUSE_DP]: True})
    assert entity_1.state == VacuumActivity.PAUSED

    device.status_updated({entity_1_cfg["id"]: "standby"})
    assert entity_1.state == VacuumActivity.IDLE
