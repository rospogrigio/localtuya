"""Discovery regression tests that do not require Home Assistant to be running."""

import binascii
import importlib.util
import json
from pathlib import Path
import random
import struct
import unittest

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "localtuya"
    / "discovery.py"
)
SPEC = importlib.util.spec_from_file_location("localtuya_discovery", MODULE_PATH)
discovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discovery)


def frame(payload):
    """Build a legacy discovery frame, including return code and CRC."""
    header = struct.pack(">IIII", 0x55AA, 1, 0x13, len(payload) + 12)
    data = header + bytes(4) + payload
    return data + struct.pack(">II", binascii.crc32(data) & 0xFFFFFFFF, 0xAA55)


def encrypt(payload):
    """Encrypt a legacy discovery payload with PKCS7 padding."""
    padding = 16 - len(payload) % 16
    cipher = Cipher(algorithms.AES(discovery.UDP_KEY), modes.ECB()).encryptor()
    return cipher.update(payload + bytes([padding]) * padding) + cipher.finalize()


class DiscoveryTests(unittest.TestCase):
    """Exercise supported packets and the observed unsupported-protocol failure."""

    def setUp(self):
        """Collect callbacks without networking or Home Assistant dependencies."""
        self.found = []
        self.protocol = discovery.TuyaDiscovery(self.found.append)
        self.address = ("192.0.2.1", 6667)

    def test_plaintext_discovery(self):
        """Continue discovering valid plaintext devices."""
        payload = {"gwId": "plaintext-device", "ip": "192.0.2.1"}
        self.protocol.datagram_received(
            frame(json.dumps(payload).encode()), self.address
        )
        self.assertEqual(self.found, [payload])

    def test_encrypted_discovery(self):
        """Continue discovering valid AES-ECB devices."""
        payload = {"gwId": "encrypted-device", "version": "3.4"}
        packet = frame(encrypt(json.dumps(payload).encode()))
        self.protocol.datagram_received(packet, self.address)
        self.assertEqual(self.found, [payload])

    def test_valid_6699_broadcast_is_ignored(self):
        """Ignore valid 3.5 broadcasts unsupported by this legacy decoder."""
        payload = b'{"gwId":"synthetic-device","version":"3.5"}'
        nonce = bytes(range(12))
        header = struct.pack(">IHIII", 0x6699, 0, 1, 0x13, 12 + len(payload) + 16)
        encrypted = AESGCM(discovery.UDP_KEY).encrypt(nonce, payload, header[4:])
        packet = header + nonce + encrypted + struct.pack(">I", 0x9966)
        self.assertEqual(
            AESGCM(discovery.UDP_KEY).decrypt(nonce, encrypted, header[4:]), payload
        )
        self.protocol.datagram_received(packet, self.address)
        self.assertEqual(self.found, [])

    def test_malformed_datagrams_are_ignored(self):
        """Do not raise on truncated, non-UTF8, or non-JSON broadcasts."""
        packets = [b"", b"abc", frame(b"\xff" * 17), frame(b"not json")]
        generator = random.Random(0)
        packets.extend(
            bytes(generator.randrange(256) for _ in range(n)) for n in range(256)
        )
        for packet in packets:
            with self.subTest(length=len(packet)):
                self.protocol.datagram_received(packet, self.address)
        self.assertEqual(self.found, [])

    def test_invalid_device_records_are_ignored(self):
        """Only dispatch JSON objects containing a non-empty string device ID."""
        records = [None, [], 12, "text", {}, {"gwId": []}, {"gwId": ""}]
        for record in records:
            with self.subTest(record=record):
                self.protocol.datagram_received(
                    frame(json.dumps(record).encode()), self.address
                )
        self.assertEqual(self.found, [])

    def test_invalid_cipher_lengths_are_rejected(self):
        """Reject invalid AES block lengths before attempting decryption."""
        for payload in (b"", b"x", bytes(17)):
            with self.subTest(length=len(payload)):
                with self.assertRaises(ValueError):
                    discovery.decrypt_udp(payload)

    def test_invalid_padding_is_rejected(self):
        """Reject a full block whose plaintext has invalid PKCS7 padding."""
        cipher = Cipher(algorithms.AES(discovery.UDP_KEY), modes.ECB()).encryptor()
        ciphertext = cipher.update(b"x" * 15 + b"\x00") + cipher.finalize()
        with self.assertRaises(ValueError):
            discovery.decrypt_udp(ciphertext)

    def test_repeat_broadcasts_still_call_back(self):
        """Preserve reconnect callbacks while deduplicating the device list."""
        packet = frame(b'{"gwId":"repeat-device"}')
        self.protocol.datagram_received(packet, self.address)
        self.protocol.datagram_received(packet, self.address)
        self.assertEqual(len(self.protocol.devices), 1)
        self.assertEqual(len(self.found), 2)


if __name__ == "__main__":
    unittest.main()
