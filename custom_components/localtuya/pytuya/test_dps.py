import pytest
from . import TuyaProtocol

dev_id = "asdfghjk"
local_key = "0123456789012345"
msg1 = '{ "dps": { "1": 5407, "10": 0, "16": true, "18": "111111111111" } }'
msg2 = '{ "dps": { "6": "CNEAJ5AACOw=" }, "t": 1613651573 }'


def listener():
    pass


@pytest.mark.asyncio
async def test_dps_decode():
    proto = TuyaProtocol(dev_id, local_key, "3.3", None, listener)

    res = proto._decode_payload(bytes(msg1, "utf-8"))
    assert res['dps'] == {'1': 5407, '10': 0, '16': True, '18': '111111111111'}

    res = proto._decode_payload(bytes(msg2, "utf-8"))
    assert res['dps'] == {'6V': 2257, '6A': 10128, '6W': 22840}
