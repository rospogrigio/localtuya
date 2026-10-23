"""Test bounded cloud requests and startup with cached local devices."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
import requests

from custom_components.localtuya import async_setup_entry
from custom_components.localtuya.cloud_api import TuyaCloudApi
from custom_components.localtuya.config_flow import ENTRIES_VERSION
from custom_components.localtuya.const import DOMAIN, TUYA_DEVICES


class CloudRequestTests(unittest.IsolatedAsyncioTestCase):
    """Exercise the real cloud client without making network requests."""

    async def test_each_http_method_has_connect_and_read_timeouts(self):
        """Bound the blocking executor request for every supported HTTP method."""
        hass = Mock(spec=HomeAssistant)
        hass.async_add_executor_job = AsyncMock(side_effect=lambda job: job())
        client = TuyaCloudApi(hass, "eu", "test", "test", "test")
        response = requests.Response()
        response.status_code = 200

        for method in ("GET", "POST", "PUT"):
            with self.subTest(method=method), patch.object(
                requests, method.lower(), return_value=response
            ) as request:
                self.assertIs(
                    await client.async_make_request(method, "/test"), response
                )
                self.assertEqual(request.call_args.kwargs.get("timeout"), (5, 10))


class CachedSetupTests(unittest.IsolatedAsyncioTestCase):
    """Cloud failures must not prevent cached local devices from starting."""

    async def check_setup(self, failed_method=None, error=None):
        """Set up one cached device with a mocked cloud service."""
        device = SimpleNamespace(async_connect=Mock())
        cloud = SimpleNamespace(
            async_get_access_token=AsyncMock(return_value="ok"),
            async_get_devices_list=AsyncMock(return_value="ok"),
        )
        if failed_method:
            getattr(cloud, failed_method).side_effect = error
        entry = SimpleNamespace(
            version=ENTRIES_VERSION,
            entry_id="test-entry",
            data={
                "region": "eu",
                "client_id": "test",
                "client_secret": "test",
                "user_id": "test",
                "no_cloud": False,
                "devices": {
                    "test-device": {
                        "local_key": "test-key",
                        "entities": [{"platform": "switch"}],
                    }
                },
            },
            add_update_listener=Mock(return_value=Mock()),
        )
        tasks = []
        hass = Mock(
            spec=HomeAssistant,
            data={DOMAIN: {TUYA_DEVICES: {}}},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        hass.async_create_task = lambda coro: tasks.append(asyncio.create_task(coro))

        with (
            patch("custom_components.localtuya.TuyaCloudApi", return_value=cloud),
            patch("custom_components.localtuya.TuyaDevice", return_value=device),
            patch(
                "custom_components.localtuya.async_remove_orphan_entities",
                new_callable=AsyncMock,
            ),
        ):
            self.assertTrue(await async_setup_entry(hass, entry))
            await asyncio.gather(*tasks)

        self.assertIs(hass.data[DOMAIN][TUYA_DEVICES]["test-device"], device)
        self.assertEqual(entry.data["devices"]["test-device"]["local_key"], "test-key")
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry, {"switch"}
        )
        device.async_connect.assert_called_once_with()
        entry.add_update_listener.assert_called_once()

    async def test_cloud_timeout_still_loads_cached_device(self):
        """A token request timeout must leave local operation available."""
        with self.assertLogs("custom_components.localtuya", level="WARNING") as logs:
            await self.check_setup(
                "async_get_access_token", requests.ReadTimeout("private-details")
            )
        self.assertNotIn("private-details", "\n".join(logs.output))

    async def test_invalid_cloud_json_still_loads_cached_device(self):
        """A device-list decoding failure must not discard cached local keys."""
        with self.assertLogs("custom_components.localtuya", level="WARNING") as logs:
            await self.check_setup(
                "async_get_devices_list", ValueError("private-details")
            )
        self.assertNotIn("private-details", "\n".join(logs.output))

    async def test_successful_cloud_setup_still_loads_device(self):
        """Normal cloud startup must keep forwarding platforms and connecting."""
        await self.check_setup()
