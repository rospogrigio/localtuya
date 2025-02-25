"""Test for localtuya."""

from . import *
from custom_components.localtuya.button import (
    LocalTuyaButton,
    DOMAIN as PLATFORM_DOMAIN,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Button 1",
                "icon": "",
                "id": "1",
                "is_passive_entity": False,
                "platform": "button",
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {"1": True, "2": False}


async def test_button():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaButton)
    entities: list[LocalTuyaButton] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaButton

    device.status_updated(DPS_STATUS)

    assert entity_1.state == None
