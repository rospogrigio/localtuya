"""Test for localtuya."""

from . import *
from custom_components.localtuya.alarm_control_panel import (
    LocalTuyaAlarmControlPanel,
    DEFAULT_SUPPORTED_MODES,
    DOMAIN as PLATFORM_DOMAIN,
    TuyaMode,
    AlarmControlPanelState,
)

CONFIG = {
    DEVICE_NAME: {
        "host": HOST,
        "add_entities": False,
        "device_id": "767823809c9c1f458745",
        "dps_strings": [
            "1 ( code: switch_1 , value: True )",
            "2 ( code: switch_2 , value: False )",
            "3 ( code: switch_3 , value: True )",
            "9 ( code: countdown_1 , value: 0 )",
            "10 ( code: countdown_2 , value: 0 )",
            "11 ( code: countdown_3 , value: 0 )",
        ],
        "enable_debug": False,
        "entities": [
            {
                "entity_category": "None",
                "friendly_name": "Button 1",
                "id": "1",
                "platform": "alarm_control_panel",
                "alarm_supported_states": DEFAULT_SUPPORTED_MODES,
            }
        ],
        "export_config": False,
        "friendly_name": "Local 3G",
        "local_key": "wV[NcWGUSFF`dSgO",
        "model": "S603",
        "node_id": None,
        "product_key": "key5nck4tavy43jp",
        "protocol_version": "3.3",
    }
}

DPS_STATUS = {"1": None}


async def test_alarm_control_panel():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaAlarmControlPanel)
    entities: list[LocalTuyaAlarmControlPanel] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities

    assert type(entity_1) is LocalTuyaAlarmControlPanel

    assert entity_1.state == None
    device.status_updated({"1": TuyaMode.ARM})
    assert entity_1.state == AlarmControlPanelState.ARMED_AWAY
    device.status_updated({"1": TuyaMode.DISARMED})
    assert entity_1.state == AlarmControlPanelState.DISARMED
    device.status_updated({"1": TuyaMode.HOME})
    assert entity_1.state == AlarmControlPanelState.ARMED_HOME
    device.status_updated({"1": TuyaMode.SOS})
    assert entity_1.state == AlarmControlPanelState.TRIGGERED
