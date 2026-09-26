"""Exercise the real TuyaDevice lifecycle methods without a Home Assistant install."""
import ast
import asyncio
import pathlib
import types
import unittest


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "custom_components/localtuya/common.py"
tree = ast.parse(SOURCE.read_text())
original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TuyaDevice")
methods = []
for node in original.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in ("_make_connection", "disconnected", "close"):
        node.decorator_list = []
        methods.append(node)
class_node = ast.ClassDef(name="DeviceUnderTest", bases=[], keywords=[], body=methods, decorator_list=[])


class FakeInterface:
    def __init__(self):
        self.closed = False

    def add_dps_to_request(self, dps):
        pass

    async def status(self):
        return {"1": True}

    def start_heartbeat(self):
        pass

    async def close(self):
        self.closed = True


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.listeners = []
        self.interfaces = []

        def connect(hass, signal, callback):
            self.listeners.append(callback)
            def unsubscribe():
                self.listeners.remove(callback)
            return unsubscribe

        async def open_connection(*args):
            interface = FakeInterface()
            self.interfaces.append(interface)
            return interface

        namespace = {
            "asyncio": asyncio,
            "pytuya": types.SimpleNamespace(connect=open_connection),
            "async_dispatcher_connect": connect,
            "async_dispatcher_send": lambda *args: None,
            "async_track_time_interval": lambda *args: None,
            "CONF_HOST": "host", "CONF_DEVICE_ID": "device_id",
            "CONF_PROTOCOL_VERSION": "protocol_version", "CONF_ENABLE_DEBUG": "enable_debug",
            "CONF_RESET_DPIDS": "reset_dpids", "CONF_SCAN_INTERVAL": "scan_interval",
            "CONF_FRIENDLY_NAME": "friendly_name", "timedelta": __import__("datetime").timedelta,
        }
        code = compile(ast.fix_missing_locations(ast.Module(body=[class_node], type_ignores=[])), str(SOURCE), "exec")
        exec(code, namespace)
        self.device = namespace["DeviceUnderTest"]()
        self.device._dev_config_entry = {"host": "127.0.0.1", "device_id": "test", "protocol_version": "3.3", "friendly_name": "test"}
        self.device._local_key = "not-a-real-key"
        self.device._hass = object()
        self.device._interface = None
        self.device._default_reset_dpids = None
        self.device._entities = []
        self.device.dps_to_request = {}
        self.device._connect_task = None
        self.device._disconnect_task = None
        self.device._unsub_interval = None
        self.device._is_closing = False
        self.device.info = self.device.warning = self.device.error = self.device.debug = lambda *args: None
        self.device.status_updated = lambda status: None

    async def test_reconnect_does_not_accumulate_dispatcher_callbacks(self):
        await self.device._make_connection()
        self.assertEqual(len(self.listeners), 1)
        for _ in range(10):
            self.device.disconnected()
            self.assertEqual(len(self.listeners), 0)
            await self.device._make_connection()
            self.assertEqual(len(self.listeners), 1)

    async def test_close_cancels_refresh_timer_even_while_connected(self):
        await self.device._make_connection()
        cancelled = []
        self.device._unsub_interval = lambda: cancelled.append(True)
        await self.device.close()
        self.assertEqual(cancelled, [True])
        self.assertEqual(len(self.listeners), 0)

    async def test_close_cleans_up_even_when_connection_task_is_cancelled(self):
        await self.device._make_connection()
        cancelled = []
        self.device._unsub_interval = lambda: cancelled.append(True)
        self.device._connect_task = asyncio.create_task(asyncio.sleep(60))
        await asyncio.sleep(0)
        await self.device.close()
        self.assertEqual(cancelled, [True])
        self.assertEqual(len(self.listeners), 0)
        self.assertTrue(self.interfaces[0].closed)
