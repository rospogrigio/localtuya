"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity, CONF_DEVICE_CLASS, EntityCategory

BUTTONS: dict[LocalTuyaEntity] = {
    # Robot Vacuum
    # https://developer.tuya.com/en/docs/iot/fsd?id=K9gf487ck1tlo
    "sd": (
        LocalTuyaEntity(
            id=DPCode.RESET_DUSTER_CLOTH,
            Name="Reset Duster Cloth",
            icon="mdi:restart",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_EDGE_BRUSH,
            Name="Reset Edge Brush",
            icon="mdi:restart",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_FILTER,
            Name="Reset Filter",
            icon="mdi:air-filter",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_MAP,
            Name="Reset Map",
            icon="mdi:map-marker-remove",
            entity_category=EntityCategory.CONFIG,
        ),
        LocalTuyaEntity(
            id=DPCode.RESET_ROLL_BRUSH,
            Name="Reset Roll Brush",
            icon="mdi:restart",
            entity_category=EntityCategory.CONFIG,
        ),
    ),
    # Wake Up Light II
    # Not documented
    "hxd": (
        LocalTuyaEntity(
            id=DPCode.SWITCH_USB6,
            Name="Snooze",
            icon="mdi:sleep",
        ),
    ),
}
