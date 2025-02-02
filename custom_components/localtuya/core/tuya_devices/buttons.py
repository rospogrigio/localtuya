"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory

BUTTONS: dict[str, tuple[LocalTuyaEntity, ...]] = {
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
}
