"""Test for localtuya."""

from . import *
from custom_components.localtuya.remote import (
    LocalTuyaRemote,
    DOMAIN as PLATFORM_DOMAIN,
)

STATE_ON = "activated"
CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": f"{PLATFORM_DOMAIN} 1",
                "icon": "",
                "id": "1",
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {
    "201": "",
    "202": "",
}


async def test_lock():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaRemote)
    entities: list[LocalTuyaRemote] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaRemote

    # device.status_updated(DPS_STATUS)
