"""Discovery module for Tuya devices.

based on tuya-convert.py from tuya-convert:
    https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py

Maintained by @xZetsubou
"""
import asyncio
import json
import logging
from hashlib import md5
from socket import inet_aton

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from Crypto.Cipher import AES

from .common import pytuya

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

PREFIX_55AA_BIN = b"\x00\x00U\xaa"
PREFIX_6699_BIN = b"\x00\x00\x66\x99"

DEFAULT_TIMEOUT = 6.0


def decrypt(msg, key):
    def _unpad(data):
        return data[: -ord(data[len(data) - 1 :])]

    return _unpad(AES.new(key, AES.MODE_ECB).decrypt(msg)).decode()


def decrypt_udp(message):
    """Decrypt encrypted UDP broadcasts."""
    if message[:4] == PREFIX_55AA_BIN:
        return decrypt(message[20:-8], UDP_KEY)
    if message[:4] == PREFIX_6699_BIN:
        unpacked = pytuya.unpack_message(message, hmac_key=UDP_KEY, no_retcode=None)
        payload = unpacked.payload.decode()
        # app sometimes has extra bytes at the end
        while payload[-1] == chr(0):
            payload = payload[:-1]
        return payload
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
        # tuyaApp_encrypted_listener = loop.create_datagram_endpoint(
        #     lambda: self, local_addr=("0.0.0.0", 7000), reuse_port=True
        # )
        self._listeners = await asyncio.gather(listener, encrypted_listener)
        _LOGGER.debug("Listening to broadcasts on UDP port 6666, 6667")

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
            # _LOGGER.debug("Bordcast from app from ip: %s", addr[0])
            _LOGGER.debug("Failed to decode bordcast from %r: %r", addr[0], data)

    def device_found(self, device):
        """Discover a new device."""
        if device.get("gwId") not in self.devices:
            self.devices[device.get("gwId")] = device
            # Sort devices by ip.
            sort_devices = sorted(
                self.devices.items(), key=lambda i: inet_aton(i[1].get("ip", "0"))
            )
            self.devices = dict(sort_devices)

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
