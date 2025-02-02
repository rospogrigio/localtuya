"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq
    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import (
    DPCode,
    LocalTuyaEntity,
)


def localtuya_lock():
    """Define localtuya lock configs"""
    data = {}
    return data


LOCKS: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # Locks
    "ms": (
        LocalTuyaEntity(
            id=(DPCode.REMOTE_UNLOCK_SWITCH, DPCode.SWITCH),
            jammed_dp=DPCode.HIJACK,
            lock_state_dp=(DPCode.CLOSED_OPENED, DPCode.OPEN_CLOSE),
        ),
    ),
}

LOCKS["jtmspro"] = LOCKS["ms"]
LOCKS["jtmsbh"] = LOCKS["ms"]
