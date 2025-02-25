"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from typing import Any
from .base import DPCode, LocalTuyaEntity, EntityCategory, CLOUD_VALUE
from homeassistant.const import CONF_BRIGHTNESS, CONF_COLOR_TEMP, CONF_SCENE

from ...const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR_TEMP_MIN_KELVIN,
    CONF_COLOR_TEMP_MAX_KELVIN,
    CONF_COLOR_TEMP_REVERSE,
    CONF_MUSIC_MODE,
)


def localtuya_light(
    lower=29, upper=1000, min_kv=2700, max_kv=6500, temp_reverse=False, music_mode=False
) -> dict[str, Any | CLOUD_VALUE]:
    """Define localtuya light configs"""
    data = {
        CONF_BRIGHTNESS_LOWER: CLOUD_VALUE(lower, CONF_BRIGHTNESS, "min"),
        CONF_BRIGHTNESS_UPPER: CLOUD_VALUE(upper, CONF_BRIGHTNESS, "max"),
        CONF_COLOR_TEMP_MIN_KELVIN: min_kv,  # CLOUD_VALUE(min_kv, CONF_COLOR_TEMP, "min")
        CONF_COLOR_TEMP_MAX_KELVIN: max_kv,  # CLOUD_VALUE(max_kv, CONF_COLOR_TEMP, "max")
        CONF_COLOR_TEMP_REVERSE: temp_reverse,
        CONF_MUSIC_MODE: music_mode,
    }

    return data


LIGHTS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Curtain Switch
    # https://developer.tuya.com/en/docs/iot/category-clkg?id=Kaiuz0gitil39
    "clkg": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_BACKLIGHT,
            name="State light",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Smart Pet Feeder
    # https://developer.tuya.com/en/docs/iot/categorycwwsq?id=Kaiuz2b6vydld
    "cwwsq": (
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name="Light",
        ),
    ),
    # String Lights
    # https://developer.tuya.com/en/docs/iot/dc?id=Kaof7taxmvadu
    "dc": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Strip Lights
    # https://developer.tuya.com/en/docs/iot/dd?id=Kaof804aibg2l
    "dd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
            color_temp=(DPCode.TEMP_VALUE_V2, DPCode.TEMP_VALUE),
            color=(DPCode.COLOUR_DATA_V2, DPCode.COLOUR_DATA),
            scene=(DPCode.SCENE_DATA_V2, DPCode.SCENE_DATA),
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
            # default_color_type=DEFAULT_COLOR_TYPE_DATA_V2,
        ),
    ),
    # Light
    # https://developer.tuya.com/en/docs/iot/categorydj?id=Kaiuyzy3eheyy
    "dj": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
            color_temp=(DPCode.TEMP_VALUE_V2, DPCode.TEMP_VALUE),
            color=(DPCode.COLOUR_DATA_V2, DPCode.COLOUR_DATA, DPCode.COLOUR_DATA_RAW),
            scene=(DPCode.SCENE_DATA_V2, DPCode.SCENE_DATA, DPCode.SCENE_DATA_RAW),
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, True),
        ),
        # Not documented
        # Based on multiple reports: manufacturer customized Dimmer 2 switches
        LocalTuyaEntity(
            id=DPCode.SWITCH_1,
            name="light",
            brightness=DPCode.BRIGHT_VALUE_1,
        ),
    ),
    # Ceiling Fan Light
    # https://developer.tuya.com/en/docs/iot/fsd?id=Kaof8eiei4c2v
    "fsd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            scene=(DPCode.SCENE_DATA, DPCode.SCENE_DATA_V2),
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        # Some ceiling fan lights use LIGHT for DPCode instead of SWITCH_LED
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name=None,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Fan Switch
    "fskg": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name="Light",
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            scene=(DPCode.SCENE_DATA, DPCode.SCENE_DATA_V2),
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        # Some ceiling fan lights use LIGHT for DPCode instead of SWITCH_LED
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name=None,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Ambient Light
    # https://developer.tuya.com/en/docs/iot/ambient-light?id=Kaiuz06amhe6g
    "fwd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            scene=(DPCode.SCENE_DATA, DPCode.SCENE_DATA_V2),
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Motion Sensor Light
    # https://developer.tuya.com/en/docs/iot/gyd?id=Kaof8a8hycfmy
    "gyd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Humidifier Light
    # https://developer.tuya.com/en/docs/iot/categoryjsq?id=Kaiuz1smr440b
    "jsq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color=DPCode.COLOUR_DATA_HSV,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_BACKLIGHT,
            name="State light",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Air Purifier
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf46h2s6dzm
    "kj": (
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name="State light",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Air conditioner
    # https://developer.tuya.com/en/docs/iot/categorykt?id=Kaiuz0z71ov2n
    "kt": (
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name="State light",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Unknown light product
    # Found as VECINO RGBW as provided by diagnostics
    # Not documented
    "mbd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color=DPCode.COLOUR_DATA,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Unknown product with light capabilities
    # Fond in some diffusers, plugs and PIR flood lights
    # Not documented
    "qjdcz": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color=DPCode.COLOUR_DATA,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Heater
    # https://developer.tuya.com/en/docs/iot/categoryqn?id=Kaiuz18kih0sm
    "qn": (
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name="State light",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Smart Camera
    # https://developer.tuya.com/en/docs/iot/categorysp?id=Kaiuz35leyo12
    "sp": (
        LocalTuyaEntity(
            id=DPCode.FLOODLIGHT_SWITCH,
            brightness=DPCode.FLOODLIGHT_LIGHTNESS,
            name="Floodlight",
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.BASIC_INDICATOR,
            name="Indicator light",
            entity_category=EntityCategory.CONFIG,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Dimmer Switch
    # https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    "tgkg": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_1,
            brightness=DPCode.BRIGHT_VALUE_1,
            brightness_upper=DPCode.BRIGHTNESS_MAX_1,
            brightness_lower=DPCode.BRIGHTNESS_MIN_1,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_2,
            name="Light 2",
            brightness=DPCode.BRIGHT_VALUE_2,
            brightness_upper=DPCode.BRIGHTNESS_MAX_2,
            brightness_lower=DPCode.BRIGHTNESS_MIN_2,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_3,
            name="Light 3",
            brightness=DPCode.BRIGHT_VALUE_3,
            brightness_upper=DPCode.BRIGHTNESS_MAX_3,
            brightness_lower=DPCode.BRIGHTNESS_MIN_3,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Dimmer
    # https://developer.tuya.com/en/docs/iot/tgq?id=Kaof8ke9il4k4
    "tgq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
            brightness_upper=DPCode.BRIGHTNESS_MAX_1,
            brightness_lower=DPCode.BRIGHTNESS_MIN_1,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_1,
            name="Light 1",
            brightness=DPCode.BRIGHT_VALUE_1,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_2,
            name="Light 2",
            brightness=DPCode.BRIGHT_VALUE_2,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_3,
            name="Light 3",
            brightness=DPCode.BRIGHT_VALUE_3,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED_4,
            name="Light 4",
            brightness=DPCode.BRIGHT_VALUE_4,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Wake Up Light II
    # Not documented
    "hxd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name="light",
            brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
            brightness_upper=DPCode.BRIGHTNESS_MAX_1,
            brightness_lower=DPCode.BRIGHTNESS_MIN_1,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Solar Light
    # https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    "tyndj": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Ceiling Light
    # https://developer.tuya.com/en/docs/iot/ceiling-light?id=Kaiuz03xxfc4r
    "xdd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color=DPCode.COLOUR_DATA,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_NIGHT_LIGHT,
            name="night_light",
        ),
    ),
    # Remote Control
    # https://developer.tuya.com/en/docs/iot/ykq?id=Kaof8ljn81aov
    "ykq": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_CONTROLLER,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_CONTROLLER,
            color_temp=DPCode.TEMP_CONTROLLER,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
    # Fan
    # https://developer.tuya.com/en/docs/iot/categoryfs?id=Kaiuz1xweel1c
    "fs": (
        LocalTuyaEntity(
            id=DPCode.LIGHT,
            name=None,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
        LocalTuyaEntity(
            id=DPCode.SWITCH_LED,
            name="light_2",
            brightness=DPCode.BRIGHT_VALUE_1,
            custom_configs=localtuya_light(29, 1000, 2700, 6500, False, False),
        ),
    ),
}

# HDMI Sync Box A1
LIGHTS["hdmipmtbq"] = (
    *LIGHTS["tgkg"],
    *LIGHTS["dj"],
)

# Dimmer
LIGHTS["tdq"] = LIGHTS["tgkg"]

# Scene Switch
# https://developer.tuya.com/en/docs/iot/f?id=K9gf7nx6jelo8
LIGHTS["cjkg"] = LIGHTS["tgkg"]

# Wireless Switch  # also can come as knob switch.
# https://developer.tuya.com/en/docs/iot/wxkg?id=Kbeo9t3ryuqm5
LIGHTS["wxkg"] = LIGHTS["tgkg"]


# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
LIGHTS["cz"] = LIGHTS["kg"]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
LIGHTS["pc"] = LIGHTS["kg"]

# Dehumidifier
# https://developer.tuya.com/en/docs/iot/categorycs?id=Kaiuz1vcz4dha
LIGHTS["cs"] = LIGHTS["jsq"]
