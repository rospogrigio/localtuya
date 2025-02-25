"""Test for localtuya."""

from . import *
from custom_components.localtuya.number import (
    LocalTuyaNumber,
    DOMAIN as PLATFORM_DOMAIN,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": f"{PLATFORM_DOMAIN} 1",
                "icon": "",
                "id": "1",
                "scaling": 0.01,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {"1": 500}


async def test_lock():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaNumber)
    entities: list[LocalTuyaNumber] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaNumber

    device.status_updated(DPS_STATUS)
    assert entity_1.native_value == 5
