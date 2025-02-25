"""Test for localtuya."""

from . import *
import math
from custom_components.localtuya.fan import LocalTuyaFan, DOMAIN as PLATFORM_DOMAIN
from homeassistant.util.percentage import (
    int_states_in_range,
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "friendly_name": "Fan",
                "entity_category": "config",
                "fan_speed_control": "3",
                "fan_direction": "4",
                "fan_direction_forward": "forward",
                "fan_direction_reverse": "reverse",
                "fan_speed_min": 1,
                "fan_speed_max": 6,
                "fan_speed_ordered_list": "disabled",
                "id": "1",
                "platform": "fan",
                "icon": "",
                "fan_oscillating_control": "6",
            },
            {
                "friendly_name": "Fan",
                "entity_category": "config",
                "fan_speed_control": "2",
                "fan_direction": "4",
                "fan_direction_forward": "forward",
                "fan_direction_reverse": "reverse",
                "fan_speed_min": 1,
                "fan_speed_max": 6,
                "fan_speed_ordered_list": "low,mid,high,max",
                "id": "21",
                "platform": "fan",
                "icon": "",
            },
        ],
    }
}

DPS_STATUS = {"1": True, "2": "mid", "3": 4, "4": "reverse", "6": True}


async def test_fan():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaFan)
    entities: list[LocalTuyaFan] = get_entites(device)

    assert len(entities) > 0
    entity_1, entity_2, *_ = entities
    assert type(entity_1) is LocalTuyaFan

    status = DPS_STATUS.copy()
    assert not entity_1.is_on
    device.status_updated(status)

    assert entity_1.is_on
    assert (
        entity_1.current_direction
        == status[CONFIG[DEVICE_NAME]["entities"][0]["fan_direction"]]
    )
    assert entity_1.oscillating == True

    speed_range = entity_1._speed_range
    speed_percentage = ranged_value_to_percentage(
        speed_range, status[CONFIG[DEVICE_NAME]["entities"][0]["fan_speed_control"]]
    )
    assert entity_1.percentage == speed_percentage

    assert percentage_to_ranged_value(speed_range, 100) == 6
    assert math.ceil(percentage_to_ranged_value(speed_range, 1)) == 1

    # Order speed.
    speed_range = entity_2._ordered_list
    speed_percentage = ordered_list_item_to_percentage(speed_range, "mid")
    assert entity_2.percentage == speed_percentage
    assert percentage_to_ordered_list_item(speed_range, 0) == speed_range[0]
    assert percentage_to_ordered_list_item(speed_range, 100) == speed_range[-1]
