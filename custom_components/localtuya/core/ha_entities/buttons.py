"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory

BUTTONS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Scene Switch
    # https://developer.tuya.com/en/docs/iot/f?id=K9gf7nx6jelo8
    "cjkg": (
        LocalTuyaEntity(
            id=DPCode.SCENE_1,
            name="Scene 1",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_2,
            name="Scene 2",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_3,
            name="Scene 3",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_4,
            name="Scene 4",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_5,
            name="Scene 5",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_6,
            name="Scene 6",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_7,
            name="Scene 7",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_8,
            name="Scene 8",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_9,
            name="Scene 9",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_10,
            name="Scene 10",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_11,
            name="Scene 11",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_12,
            name="Scene 12",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_13,
            name="Scene 13",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_14,
            name="Scene 14",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_15,
            name="Scene 15",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_16,
            name="Scene 16",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_17,
            name="Scene 17",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_18,
            name="Scene 18",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_18,
            name="Scene 18",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_19,
            name="Scene 19",
            icon="mdi:palette",
        ),
        LocalTuyaEntity(
            id=DPCode.SCENE_20,
            name="Scene 20",
            icon="mdi:palette",
        ),
    ),
    # Curtain
    # Note: Multiple curtains isn't documented
    # https://developer.tuya.com/en/docs/iot/categorycl?id=Kaiuz1hnpo7df
    "cl": (
        LocalTuyaEntity(
            id=DPCode.REMOTE_REGISTER,
            name="Pair Remote",
            icon="mdi:remote",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.RESET_DUSTER_CLOTH,
            name="Reset Duster Cloth",
            icon="mdi:restart",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_EDGE_BRUSH,
            name="Reset Edge Brush",
            icon="mdi:restart",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_FILTER,
            name="Reset Filter",
            icon="mdi:air-filter",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_MAP,
            name="Reset Map",
            icon="mdi:map-marker-remove",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_ROLL_BRUSH,
            name="Reset Roll Brush",
            icon="mdi:restart",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Wake Up Light II
    # Not documented
    "hxd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB6,
            name="Snooze",
            icon="mdi:sleep",
        ),
    ),
    "cz": (
        LocalTuyaEntity(
            id=DPCode.CLEAR_ENERGY,
            name="Clear Energy",
            icon="mdi:lightning-bolt-circle",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
}

# Wireless Switch  # also can come as knob switch.
# https://developer.tuya.com/en/docs/iot/wxkg?id=Kbeo9t3ryuqm5
BUTTONS["wxkg"] = BUTTONS["cjkg"]
