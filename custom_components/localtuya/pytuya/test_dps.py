import pytest
from . import TuyaProtocol

DEV_ID = "asdfghjk"
LOCAL_KEY = "0123456789012345"
MSG1 = '{ "dps": { "1": 5407, "10": 0, "16": true, "18": "111111111111" } }'
MSG2 = '{ "dps": { "6": "CNEAJ5AACOw=" }, "t": 1613651573 }'


def listener():
    pass


@pytest.mark.asyncio
async def test_dps_decode():
    proto = TuyaProtocol(DEV_ID, LOCAL_KEY, "3.3", None, listener)

    res = proto._decode_payload(bytes(MSG1, "utf-8"))
    assert res['dps'] == {'1': 5407, '10': 0, '16': True, '18': '111111111111'}

    res = proto._decode_payload(bytes(MSG2, "utf-8"))
    assert res['dps'] == {'6001': 10128, '6002': 22840, '6003': 2257}
