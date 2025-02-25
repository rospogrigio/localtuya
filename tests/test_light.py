"""Test for localtuya."""

from . import *
from custom_components.localtuya.light import (
    LocalTuyaLight,
    DOMAIN as PLATFORM_DOMAIN,
    ColorMode,
)

CONFIG = {
    DEVICE_NAME: {
        **DEVICE_CONFIG,
        "entities": [
            {
                "id": "20",
                "color_mode": "21",
                "brightness": "22",
                "color_temp": "23",
                "color": "24",
                "scene": "25",
                "brightness_lower": 10,
                "brightness_upper": 1000,
                "color_temp_min_kelvin": 2700,
                "color_temp_max_kelvin": 6500,
                "color_temp_reverse": False,
                "music_mode": True,
                "friendly_name": None,
                "icon": "",
                "entity_category": "None",
                "platform": "light",
            }
        ],
    }
}

DPS_STATUS = {
    "20": True,
    "21": "white",
    "22": 600,
    "23": 1000,
    "24": "000403e8000c",
    "25": "010e0d000084000003e800000000",
}
ENC_COLOR = "0319090087db1c"
BLE_COLOR = "0319090087db1c"


async def test_light():
    device = await init(CONFIG, PLATFORM_DOMAIN, LocalTuyaLight)
    entities: list[LocalTuyaLight] = get_entites(device)

    assert len(entities) > 0
    entity_1, *_ = entities
    assert type(entity_1) is LocalTuyaLight

    status = DPS_STATUS.copy()
    device.status_updated(status)

    assert entity_1.state == "on"
    assert entity_1.brightness is not None
    assert entity_1.is_white_mode
    assert entity_1.color_temp_kelvin is not None

    device.status_updated({"21": "colour"})
    assert entity_1.hs_color is not None

    device.status_updated({"24": ENC_COLOR})
    sat, brightness = entity_1.hs_color
    assert sat < 360 and brightness <= 100

    device.status_updated({"21": "music"})
    assert entity_1.is_music_mode

    device.status_updated({"21": "scene"})
    assert entity_1.effect is not None
    assert entity_1.is_scene_mode

    # Bluetooth
    # device.status_updated({"21": "colour", "24": "AHhkZA==", "25": ""})
