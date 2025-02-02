"""Discovery module for Tuya devices.

based on tuya-convert.py from tuya-convert:
    https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py

Maintained by @xZetsubou
"""
import asyncio
import json
import logging
from hashlib import md5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from Crypto.Cipher import AES

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

PERFIX_APP_BROADCAST = b"\x00\x00f\x99\x00"
PREFIX_55AA_BIN = b"\x00\x00U\xaa"
PREFIX_6699_BIN = b"\x00\x00\x66\x99"

DEFAULT_TIMEOUT = 6.0


def decrypt(msg, key):
    def _unpad(data):
        return data[: -ord(data[len(data) - 1 :])]

    return _unpad(AES.new(key, AES.MODE_ECB).decrypt(msg)).decode()


def decrypt_gcm(msg, key):
    nonce = msg[:12]
    return AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt(msg[12:]).decode()


def decrypt_udp(message):
    """Decrypt encrypted UDP broadcasts."""
    if message[:4] == PREFIX_55AA_BIN:
        return decrypt(message[20:-8], UDP_KEY)
    if message[:4] == PREFIX_6699_BIN:
        unpacked = decrypt_gcm(message, hmac_key=UDP_KEY)
        # strip return code if present
        if unpacked[:4] == (chr(0) * 4):
            unpacked = unpacked[4:]
        # app sometimes has extra bytes at the end
        while unpacked[-1] == chr(0):
            unpacked = unpacked[:-1]
        return unpacked
    return decrypt(message, UDP_KEY)


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
        tuyaApp_encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 7000), reuse_port=True
        )

        self._listeners = await asyncio.gather(
            listener, encrypted_listener, tuyaApp_encrypted_listener
        )
        _LOGGER.debug("Listening to broadcasts on UDP port 6666, 6667 and 7000")

    def close(self):
        """Stop discovery."""
        self._callback = None
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        """Handle received broadcast message."""
        try:
            try:
                data = decrypt_udp(data)
            except Exception:  # pylint: disable=broad-except
                data = data.decode()
            decoded = json.loads(data)
            self.device_found(decoded)
        except:
            if data[:5] == PERFIX_APP_BROADCAST:
                _LOGGER.debug("Broadcast from app at ip: %s", addr[0])
            else:
                _LOGGER.debug("Failed to decode broadcast from %r: %r", addr[0], data)

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
