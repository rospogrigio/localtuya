"""Test for localtuya."""

from . import *
from custom_components.localtuya.siren import (
    LocalTuyaSiren,
    DOMAIN as PLATFORM_DOMAIN,
)

STATE_ON = "activated"
CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "friendly_name": "Siren",
                "id": "5",
                "state_on": STATE_ON,
                "is_passive_entity": False,
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {"5": STATE_ON}


async def test_siren():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaSiren)
    entities: list[LocalTuyaSiren] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaSiren

    assert not entity_1.is_on
    device.status_updated(DPS_STATUS)
    assert entity_1.is_on
