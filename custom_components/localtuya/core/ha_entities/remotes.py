"""
    This a file contains available tuya data
    https://developer.tuya.com/en/docs/iot/standarddescription?id=K9i5ql6waswzq

    Credits: official HA Tuya integration.
    Modified by: xZetsubou
"""

from .base import DPCode, LocalTuyaEntity


CONF_RECEIVE_DP = "receive_dp"


# def localtuya_remote(_):
#     """Define localtuya fan configs"""
#     data = {}
#     return data


REMOTES: dict[str, tuple[LocalTuyaEntity, ...]] = {
    # IR Remote
    # not documented
    "wnykq": (
        LocalTuyaEntity(
            id=(DPCode.IR_SEND, DPCode.CONTROL),
            receive_dp=(DPCode.IR_STUDY_CODE, DPCode.STUDY_CODE),
            key_study_dp=DPCode.KEY_STUDY,
        ),
    ),
}
