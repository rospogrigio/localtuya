"""Discovery module for Tuya devices.

based on tuya-convert.py from tuya-convert:
    https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py

Maintained by @xZetsubou
"""

import os
import asyncio
import json
import logging
from hashlib import md5
from socket import inet_aton

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .entity import pytuya

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

PREFIX_55AA_BIN = b"\x00\x00U\xaa"
PREFIX_6699_BIN = b"\x00\x00\x66\x99"
UDP_COMMAND = b"\x00\x00\x00\x00"

DEFAULT_TIMEOUT = 6.0


def decrypt(msg, key):
    def _unpad(data):
        return data[: -ord(data[len(data) - 1 :])]

    cipher = Cipher(algorithms.AES(key), modes.ECB(), default_backend())
    decryptor = cipher.decryptor()
    return _unpad(decryptor.update(msg) + decryptor.finalize()).decode()


def decrypt_udp(message):
    """Decrypt encrypted UDP broadcasts."""
    if message[:4] == PREFIX_55AA_BIN:
        payload = message[20:-8]
        if message[8:12] == UDP_COMMAND:
            return payload
        return decrypt(payload, UDP_KEY)
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
        op_reuse_port = {"reuse_port": True} if os.name != "nt" else {}
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666), **op_reuse_port
        )
        encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6667), **op_reuse_port
        )
        # tuyaApp_encrypted_listener = loop.create_datagram_endpoint(
        #     lambda: self, local_addr=("0.0.0.0", 7000), **op_reuse_port
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
            _LOGGER.debug("Failed to decode broadcast from %r: %r", addr[0], data)

    def device_found(self, device):
        """Discover a new device."""
        gwid, ip = device.get("gwId"), device.get("ip")
        # If device found but the ip changed.
        if gwid in self.devices and (self.devices[gwid].get("ip") != ip):
            self.devices.pop(gwid)

        if gwid not in self.devices:
            self.devices[gwid] = device
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
