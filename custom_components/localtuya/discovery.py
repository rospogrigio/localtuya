"""Discovery module for Tuya devices.

Entirely based on tuya-convert.py from tuya-convert:

https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py
"""
import asyncio
import json
import logging
from hashlib import md5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

DEFAULT_TIMEOUT = 6.0


def decrypt_udp(message):
    """Decrypt encrypted UDP broadcasts."""

    if not message or len(message) % 16:
        raise ValueError("Invalid encrypted discovery payload length")
    cipher = Cipher(algorithms.AES(UDP_KEY), modes.ECB(), default_backend())
    decryptor = cipher.decryptor()
    decoded = decryptor.update(message) + decryptor.finalize()
    padding = decoded[-1]
    if not 1 <= padding <= 16 or decoded[-padding:] != bytes([padding]) * padding:
        raise ValueError("Invalid encrypted discovery padding")
    return decoded[:-padding].decode("utf-8")

class TuyaDiscovery(asyncio.DatagramProtocol):
    """Datagram handler listening for Tuya broadcast messages."""

    def __init__(self, callback=None):
        """Initialize a new BaseDiscovery."""
        self.devices = {}
        self._listeners = []
        self._callback = callback

    async def start(self):
        """Start discovery by listening to broadcasts."""
        loop = asyncio.get_running_loop()
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666), reuse_port=True
        )
        encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6667), reuse_port=True
        )

        self._listeners = await asyncio.gather(listener, encrypted_listener)
        _LOGGER.debug("Listening to broadcasts on UDP port 6666 and 6667")

    def close(self):
        """Stop discovery."""
        self._callback = None
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        """Handle received broadcast message."""
        if not isinstance(data, (bytes, bytearray)) or len(data) <= 28:
            return
        # This decoder supports the existing 55aa discovery envelope only.
        # New/unknown binary formats must not fall through to UTF-8 decoding.
        if data[:4] != b"\x00\x00\x55\xaa" or data[-4:] != b"\x00\x00\xaa\x55":
            return
        payload = data[20:-8]
        try:
            text = decrypt_udp(payload)
        except (ValueError, UnicodeDecodeError):
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                return
        try:
            decoded = json.loads(text)
        except (ValueError, TypeError):
            return
        if (
            not isinstance(decoded, dict)
            or not isinstance(decoded.get("gwId"), str)
            or not decoded["gwId"]
        ):
            return
        self.device_found(decoded)

    def device_found(self, device):
        """Discover a new device."""
        if device.get("gwId") not in self.devices:
            self.devices[device.get("gwId")] = device
            _LOGGER.debug("Discovered device: %s", device)

        if self._callback:
            self._callback(device)


async def discover():
    """Discover and return devices on local network."""
    discovery = TuyaDiscovery()
    try:
        await discovery.start()
        await asyncio.sleep(DEFAULT_TIMEOUT)
    finally:
        discovery.close()
    return discovery.devices
