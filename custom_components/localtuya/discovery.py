"""Discovery module for Tuya devices.

Entirely based on tuya-convert.py from tuya-convert:

https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py
"""
import json
import asyncio
import logging
from hashlib import md5

from Cryptodome.Cipher import AES

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()


def decrypt_udp(message):
    """Decrypt encrypted UDP broadcasts."""
    def _unpad(data):
        return data[:-ord(data[len(data) - 1:])]

    return _unpad(AES.new(UDP_KEY, AES.MODE_ECB).decrypt(message)).decode()


class TuyaDiscovery(asyncio.DatagramProtocol):
    """Datagram handler listening for Tuya broadcast messages."""

    def __init__(self, found_devices):
        """Initialize a new TuyaDiscovery instance."""
        self.found_devices = found_devices

    def datagram_received(self, data, addr):
        """Handle received broadcast message."""
        data = data[20:-8]
        try:
            data = decrypt_udp(data)
        except Exception:
            data = data.decode()

        decoded = json.loads(data)
        if decoded.get("ip") not in self.found_devices:
            self.found_devices[decoded.get("ip")] = decoded
            _LOGGER.debug("Discovered device: %s", decoded)


async def discover(timeout, loop):
    """Discover and return Tuya devices on the network."""
    found_devices = {}

    def proto_factory():
        return TuyaDiscovery(found_devices)

    listener = loop.create_datagram_endpoint(
        proto_factory, local_addr=("0.0.0.0", 6666)
    )
    encrypted_listener = loop.create_datagram_endpoint(
        proto_factory, local_addr=("0.0.0.0", 6667)
    )

    listeners = await asyncio.gather(listener, encrypted_listener)
    _LOGGER.debug("Listening to broadcasts on UDP port 6666 and 6667")

    try:
        await asyncio.sleep(timeout)
    finally:
        for transport, _ in listeners:
            transport.close()

    return found_devices


def main():
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(discover(5, loop))
    print(res)


if __name__ == "__main__":
    main()
