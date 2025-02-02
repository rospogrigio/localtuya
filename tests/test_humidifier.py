"""Test for localtuya."""

from . import *
from custom_components.localtuya.humidifier import (
    LocalTuyaHumidifier,
    DOMAIN as PLATFORM_DOMAIN,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "device_class": "dehumidifier",
                "entity_category": "None",
                "friendly_name": "",
                "humidifier_available_modes": {
                    "continuous": "Continuous",
                    "dehumidify": "Dehumidify",
                    "drying": "Drying",
                },
                "humidifier_current_humidity_dp": "16",
                "humidifier_mode_dp": "4",
                "humidifier_set_humidity_dp": "2",
                "icon": "",
                "id": "1",
                "max_humidity": 70,
                "min_humidity": 35,
                "platform": "humidifier",
            },
        ],
    }
}
ENTITIES = CONFIG[DEVICE_NAME]["entities"]
DPS_STATUS = {"1": True, "2": 34, "4": "drying", "16": 34}


async def test_humidifier():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaHumidifier)
    entities: list[LocalTuyaHumidifier] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaHumidifier

    assert entity_1.state == None

    status = DPS_STATUS.copy()
    device.status_updated(status)

    assert entity_1.state == "on"
    assert entity_1.current_humidity == status.get(
        ENTITIES[0]["humidifier_current_humidity_dp"]
    )
    assert (
        entity_1.mode
        == ENTITIES[0]["humidifier_available_modes"][
            status[ENTITIES[0]["humidifier_mode_dp"]]
        ]
    )
    assert (
        entity_1.target_humidity
        == status[ENTITIES[0]["humidifier_current_humidity_dp"]]
    )
