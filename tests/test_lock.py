"""Test for localtuya."""

from . import *
from custom_components.localtuya.lock import LocalTuyaLock, DOMAIN as PLATFORM_DOMAIN

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
                "lock_state_dp": "2",
                "jammed_dp": "3",
                "platform": PLATFORM_DOMAIN,
                "restore_on_reconnect": False,
            }
        ],
    }
}

DPS_STATUS = {"1": None, "2": "unlocked"}


async def test_lock():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaLock)
    entities: list[LocalTuyaLock] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaLock

    device.status_updated(DPS_STATUS)
    assert entity_1.state == "unlocked"

    device.status_updated({**DPS_STATUS, **{"1": True}})
    assert not entity_1.is_locked

    assert not entity_1.is_jammed
    device.status_updated({**DPS_STATUS, **{"3": True}})
    assert entity_1.is_jammed
