"""Test for localtuya."""

from . import *
from custom_components.localtuya.select import (
    LocalTuyaSelect,
    DOMAIN as PLATFORM_DOMAIN,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "config",
                "friendly_name": "Motor Direction",
                "icon": "mdi:swap-vertical",
                "id": "5",
                "is_passive_entity": False,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
                "select_options": {"back": "Back", "forward": "Forward"},
            }
        ],
    }
}

DPS_STATUS = {"5": "back"}


async def test_lock():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaSelect)
    entities: list[LocalTuyaSelect] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaSelect

    device.status_updated(DPS_STATUS)
    assert (
        entity_1.state in CONFIG[DEVICE_NAME]["entities"][0]["select_options"].values()
    )
