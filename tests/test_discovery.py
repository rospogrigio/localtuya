"""Regression tests for malformed Tuya discovery datagrams."""
import importlib.util
import logging
import pathlib
import unittest
from unittest.mock import patch


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "custom_components/localtuya/discovery.py"
spec = importlib.util.spec_from_file_location("localtuya_discovery", SOURCE)
discovery_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery_module)


class DiscoveryTests(unittest.TestCase):
    def test_invalid_binary_datagram_does_not_escape_callback(self):
        protocol = discovery_module.TuyaDiscovery()
        packet = bytes(20) + b"\x90\xa6" + bytes(8)
        with self.assertLogs(discovery_module._LOGGER, level=logging.DEBUG):
            protocol.datagram_received(packet, ("127.0.0.1", 6667))
        self.assertEqual(protocol.devices, {})

    def test_valid_plaintext_datagram_still_discovers_device(self):
        seen = []
        protocol = discovery_module.TuyaDiscovery(seen.append)
        packet = bytes(20) + b'{"gwId":"test","ip":"127.0.0.1"}' + bytes(8)
        with patch.object(discovery_module, "decrypt_udp", side_effect=ValueError("not encrypted")):
            protocol.datagram_received(packet, ("127.0.0.1", 6666))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["gwId"], "test")

    def test_non_object_json_does_not_escape_callback(self):
        protocol = discovery_module.TuyaDiscovery()
        with patch.object(discovery_module, "decrypt_udp", return_value="null"):
            with self.assertLogs(discovery_module._LOGGER, level=logging.DEBUG):
                protocol.datagram_received(bytes(32), ("127.0.0.1", 6667))
        self.assertEqual(protocol.devices, {})
