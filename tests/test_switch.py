"""Test for localtuya."""

from . import *
from homeassistant.const import EntityCategory
from custom_components.localtuya.switch import LocalTuyaSwitch, DOMAIN as SWITCH_DOMAIN

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Switch 1",
                "icon": "",
                "id": "1",
                "is_passive_entity": False,
                "platform": "switch",
                "restore_on_reconnect": False,
            },
            {
                "entity_category": "config",
                "friendly_name": "Switch 2",
                "icon": "",
                "id": "2",
                "is_passive_entity": False,
                "platform": "switch",
                "restore_on_reconnect": False,
            },
        ],
    }
}

DPS_STATUS = {"1": True, "2": False}


async def test_switch():
    device = await init(CONFIG, SWITCH_DOMAIN, LocalTuyaSwitch)
    entities: list[LocalTuyaSwitch] = get_entites(device)

    assert len(entities) > 0
    entity_sw1, entity_sw2, *_ = entities
    assert type(entity_sw1) is LocalTuyaSwitch

    assert entity_sw1.state == None
    device.status_updated(DPS_STATUS)

    assert entity_sw1.state == "on"
    assert entity_sw2.state == "off"
    assert entity_sw2.entity_category == EntityCategory.CONFIG
