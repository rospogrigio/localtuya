"""Regression tests for command responses that also contain a status update."""

import asyncio
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

# Load the standalone protocol module without importing the HA integration.
MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/localtuya/pytuya/__init__.py"
)
SPEC = importlib.util.spec_from_file_location("pytuya", MODULE_PATH)
pytuya = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pytuya)


class MessageDispatcherTests(unittest.IsolatedAsyncioTestCase):
    """Exercise status delivery independently of response ordering."""

    async def asyncSetUp(self):
        """Create a dispatcher and an entity status listener."""
        self.status_listener = Mock()
        self.dispatcher = pytuya.MessageDispatcher(
            "test-device", self.status_listener, 3.4, b"0123456789abcdef", False
        )

    async def start_waiter(self, seqno, command):
        """Register the response listener before delivering a packet."""
        waiter = asyncio.create_task(self.dispatcher.wait_for(seqno, command))
        await asyncio.sleep(0)
        self.assertIn(seqno, self.dispatcher.listeners)
        return waiter

    async def test_status_matching_command_updates_listener(self):
        """A matching STATUS must reach both the entity and command waiter."""
        waiter = await self.start_waiter(42, pytuya.CONTROL_NEW)
        status = pytuya.TuyaMessage(42, pytuya.STATUS, 0, b'{"dps":{"1":false}}', 0)

        self.dispatcher._dispatch(status)

        self.status_listener.assert_called_once_with(status)
        self.assertIs(await waiter, status)
        self.assertNotIn(42, self.dispatcher.listeners)

    async def test_status_before_ack_is_not_lost(self):
        """A later ACK must not suppress an earlier matching status report."""
        waiter = await self.start_waiter(42, pytuya.CONTROL_NEW)
        status = pytuya.TuyaMessage(42, pytuya.STATUS, 0, b'{"dps":{"1":false}}', 0)
        ack = pytuya.TuyaMessage(43, pytuya.CONTROL_NEW, 0, b"", 0)

        self.dispatcher._dispatch(status)
        self.dispatcher._dispatch(ack)

        self.assertIs(await waiter, status)
        self.status_listener.assert_called_once_with(status)

    async def test_ack_before_status(self):
        """An ACK may complete the command before an unsolicited status."""
        waiter = await self.start_waiter(42, pytuya.CONTROL_NEW)
        ack = pytuya.TuyaMessage(42, pytuya.CONTROL_NEW, 0, b"", 0)
        status = pytuya.TuyaMessage(43, pytuya.STATUS, 0, b'{"dps":{"1":true}}', 0)

        self.dispatcher._dispatch(ack)
        self.assertIs(await waiter, ack)
        self.status_listener.assert_not_called()
        self.dispatcher._dispatch(status)

        self.status_listener.assert_called_once_with(status)

    async def test_unsolicited_status(self):
        """Status reports without a pending command still reach the listener."""
        status = pytuya.TuyaMessage(43, pytuya.STATUS, 0, b'{"dps":{"1":true}}', 0)
        self.dispatcher._dispatch(status)
        self.status_listener.assert_called_once_with(status)

    async def test_heartbeat_response(self):
        """Heartbeat replies still release their special waiter."""
        seqno = self.dispatcher.HEARTBEAT_SEQNO
        waiter = await self.start_waiter(seqno, pytuya.HEART_BEAT)
        heartbeat = pytuya.TuyaMessage(42, pytuya.HEART_BEAT, 0, b"", 0)
        self.dispatcher._dispatch(heartbeat)
        self.assertIs(await waiter, heartbeat)
        self.status_listener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
