"""Tuya Device API"""

from __future__ import annotations
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Callable, Coroutine, NamedTuple
from functools import partial


from homeassistant.core import HomeAssistant, CALLBACK_TYPE, callback, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_DEVICES, CONF_HOST, CONF_DEVICE_ID
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
    dispatcher_send,
)

from .core import pytuya
from .core.cloud_api import TuyaCloudApi
from .const import (
    ATTR_UPDATED_AT,
    CONF_GATEWAY_ID,
    CONF_LOCAL_KEY,
    CONF_DEVICE_NODE_ID,
    CONF_MODEL,
    CONF_PASSIVE_ENTITY,
    CONF_PROTOCOL_VERSION,
    CONF_RESET_DPIDS,
    CONF_RESTORE_ON_RECONNECT,
    CONF_NODE_ID,
    CONF_TUYA_IP,
    DATA_DISCOVERY,
    DOMAIN,
    DeviceConfig,
    RESTORE_STATES,
)

_LOGGER = logging.getLogger(__name__)
RECONNECT_INTERVAL = timedelta(seconds=5)


class HassLocalTuyaData(NamedTuple):
    """LocalTuya data stored in homeassistant data object."""

    cloud_data: TuyaCloudApi
    devices: dict[str, TuyaDevice]
    unsub_listeners: list[CALLBACK_TYPE,]


class TuyaDevice(pytuya.TuyaListener, pytuya.ContextualLogger):
    """Cache wrapper for pytuya.TuyaInterface."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device_config: dict,
        fake_gateway=False,
    ):
        """Initialize the cache."""
        super().__init__()
        self._hass = hass
        self._entry = entry
        self._hass_entry: HassLocalTuyaData = None
        self._device_config = DeviceConfig(device_config.copy())

        self._interface = None

        # For SubDevices
        self._node_id: str = self._device_config.node_id
        self._fake_gateway = fake_gateway
        self._gateway: TuyaDevice = None
        self.sub_devices: dict[str, TuyaDevice] = {}

        self._status = {}
        # Sleep timer, a device that reports the status every x seconds then goes into sleep.
        self._last_update_time: int = int(time.time()) - 5
        self._pending_status: dict[str, dict[str, Any]] = {}

        self.dps_to_request = {}
        self._is_closing = False
        self._connect_task: asyncio.Task | None = None
        self._unsub_refresh: CALLBACK_TYPE | None = None
        self._reconnect_task = False
        self._call_on_close: list[CALLBACK_TYPE] = []
        self._entities = []
        self._local_key: str = self._device_config.local_key
        self._default_reset_dpids: list | None = None
        if reset_dps := self._device_config.reset_dps:
            self._default_reset_dpids = [int(id.strip()) for id in reset_dps.split(",")]

        dev = self._device_config
        self.set_logger(_LOGGER, dev.id, dev.enable_debug, dev.name)

        # This has to be done in case the device type is type_0d
        for dp in self._device_config.dps_strings:
            self.dps_to_request[dp.split(" ")[0]] = None

    def add_entities(self, entities):
        """Set the entities associated with this device."""
        self._entities.extend(entities)

    @property
    def is_connecting(self):
        """Return whether device is currently connecting."""
        return self._connect_task is not None

    @property
    def connected(self):
        """Return if connected to device."""
        return self._interface and self._interface.is_connected

    @property
    def is_subdevice(self):
        """Return whether this is a subdevice or not."""
        return self._node_id and not self._fake_gateway

    @property
    def is_sleep(self):
        """Return whether the device is sleep or not."""
        device_sleep = self._device_config.sleep_time
        if device_sleep > 0:
            setattr(self, "low_power", True)
        last_update = int(time.time()) - self._last_update_time
        is_sleep = last_update < device_sleep

        return device_sleep > 0 and is_sleep

    async def async_connect(self, _now=None) -> None:
        """Connect to device if not already connected."""
        if not self._hass_entry:
            self._hass_entry = self._hass.data[DOMAIN][self._entry.entry_id]

        if self._is_closing or self.is_connecting:
            return

        if self.connected:
            return self._dispatch_status()

        self._connect_task = asyncio.create_task(self._make_connection())

        if not self.is_sleep and not self.is_subdevice:
            await self._connect_task

    async def _get_gateway(self):
        """Return the gateway device of this sub device."""
        if not self._node_id:
            return
        gateway: TuyaDevice
        node_host = self._device_config.host
        devices = self._hass_entry.devices

        # Sub to gateway.
        if gateway := devices.get(node_host):
            # Ensure that sub-device still on the same gateway device.
            if gateway._local_key != self._local_key:
                self.warning("Sub-device localkey doesn't match the gateway localkey")
                self._local_key = gateway._local_key

            self.debug(f"Uses the gateway: {gateway._device_config.name}")
            self._gateway = gateway
            gateway.sub_devices[self._node_id] = self
            return gateway
        else:
            self.error(f"Couldn't find the gateway for: {self._node_id}")
        return None

    async def _make_connection(self):
        """Subscribe localtuya entity events."""
        if self.is_sleep and not self._status:
            self.status_updated(RESTORE_STATES)

        name, host = self._device_config.name, self._device_config.host
        retry = 0
        max_retries = 3
        update_localkey = False

        self.debug(f"Trying to connect to: {host}...", force=True)
        # Connect to the device, interface should be connected for next steps.
        while retry < max_retries:
            retry += 1
            try:
                if self.is_subdevice:
                    gateway = await self._get_gateway()
                    if not gateway or (not gateway.connected and gateway.is_connecting):
                        return await self.abort_connect()
                    self._interface = gateway._interface
                    if self._device_config.enable_debug:
                        self._interface.enable_debug(True, gateway._device_config.name)
                else:
                    self._interface = await pytuya.connect(
                        self._device_config.host,
                        self._device_config.id,
                        self._local_key,
                        float(self._device_config.protocol_version),
                        self._device_config.enable_debug,
                        self,
                    )
                    self._interface.enable_debug(self._device_config.enable_debug, name)
                self._interface.add_dps_to_request(self.dps_to_request)
                break  # Succeed break while loop
            except OSError as e:
                await self.abort_connect()
                if retry >= max_retries or e.errno == pytuya.errno.EHOSTUNREACH:
                    self.warning(f"Connection failed: {e}")
                    break
            except Exception as ex:  # pylint: disable=broad-except
                await self.abort_connect()
                if retry >= max_retries and not self.is_sleep:
                    self.warning(f"Failed to connect to {host}: {str(ex)}")
                if "key" in str(ex):
                    update_localkey = True
                    break

        # Get device status and configure DPS.
        if self.connected:
            try:
                # If reset dpids set - then assume reset is needed before status.
                reset_dpids = self._default_reset_dpids
                if (reset_dpids is not None) and (len(reset_dpids) > 0):
                    self.debug(f"Resetting cmd for DP IDs: {reset_dpids}")
                    # Assume we want to request status updated for the same set of DP_IDs as the reset ones.
                    self._interface.set_updatedps_list(reset_dpids)

                    # Reset the interface
                    await self._interface.reset(reset_dpids, cid=self._node_id)

                self.debug("Retrieving initial state")
                # Usually we use status instead of detect_available_dps, but some device doesn't reports all dps when ask for status.
                status = await self._interface.status(cid=self._node_id)
                if status is None:
                    raise Exception("Failed to retrieve status")

                self._interface.start_heartbeat()
                self.status_updated(status)
            except (UnicodeDecodeError, pytuya.DecodeError) as e:
                self.exception(f"Handshake with {host} failed: due to {type(e)}: {e}")
                await self.abort_connect()
                update_localkey = True
            except Exception as e:
                if not (self._fake_gateway and "Not found" in str(e)):
                    e = "Sub device is not connected" if self.is_subdevice else e
                    self.warning(f"Handshake with {host} failed: {e}")
                    await self.abort_connect()
                    if self.is_subdevice:
                        update_localkey = True
            except:
                if self._fake_gateway:
                    self.warning(f"Failed to use {name} as gateway.")
                    await self.abort_connect()
                    update_localkey = True

        # Connect and configure the entities, at this point the device should be ready to get commands.
        if self.connected:
            # Attempt to restore status for all entities that need to first set
            # the DPS value before the device will respond with status.
            for entity in self._entities:
                await entity.restore_state_when_connected()

            def _new_entity_handler(entity_id):
                self.debug(f"New entity {entity_id} was added to {host}")
                self._dispatch_status()

            signal = f"localtuya_entity_{self._device_config.id}"
            self._call_on_close.append(
                async_dispatcher_connect(self._hass, signal, _new_entity_handler)
            )

            if (scan_inv := int(self._device_config.scan_interval)) > 0:
                self._unsub_refresh = async_track_time_interval(
                    self._hass, self._async_refresh, timedelta(seconds=scan_inv)
                )

            self._connect_task = None
            self.debug(f"Success: connected to: {host}", force=True)

            if self.sub_devices:
                for subdevice in self.sub_devices.values():
                    self._hass.async_create_task(subdevice.async_connect())

                self._interface.start_sub_devices_heartbeat()

            if not self._status and "0" in self._device_config.manual_dps.split(","):
                self.status_updated(RESTORE_STATES)

            if self._pending_status:
                await self.set_status()

        # If not connected try to handle the errors.
        if not self.connected:
            if not self._reconnect_task:
                self._call_on_close.append(
                    asyncio.create_task(self._async_reconnect()).cancel
                )
            if update_localkey:
                # Check if the cloud device info has changed!.
                await self.update_local_key()

        self._connect_task = None

    async def abort_connect(self):
        """Abort the connect process to the interface[device]"""
        if self.is_subdevice:
            self._interface = None
            self._connect_task = None

        if self._interface is not None:
            await self._interface.close()
            self._interface = None

    async def check_connection(self):
        """Ensure that the device is not still connecting; if it is, wait for it."""
        if not self.connected and self._connect_task:
            await self._connect_task
        if not self.connected and self._gateway and self._gateway._connect_task:
            await self._gateway._connect_task
        if not self.connected:
            self.error(f"Not connected to device {self._device_config.name}")

    async def close(self):
        """Close connection and stop re-connect loop."""
        self._is_closing = True
        self._shutdown_entities()

        for callback in self._call_on_close:
            callback()

        if self._connect_task is not None:
            self._connect_task.cancel()
            await self._connect_task
            self._connect_task = None
        if self._interface is not None:
            await self._interface.close()
            self._interface = None
        self.debug(f"Closed connection", force=True)

    async def update_local_key(self):
        """Retrieve updated local_key from Cloud API and update the config_entry."""
        dev_id = self._device_config.id

        cloud_api = self._hass_entry.cloud_data
        await cloud_api.async_get_devices_list()
        discovery = self._hass.data[DOMAIN].get(DATA_DISCOVERY)

        cloud_devs = cloud_api.device_list
        if dev_id in cloud_devs:
            cloud_localkey = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
            if not cloud_localkey or self._local_key == cloud_localkey:
                return

            new_data = self._entry.data.copy()
            self._local_key = cloud_localkey

            if self._node_id:
                from .core.helpers import get_gateway_by_deviceid

                # Update Node ID.
                if new_node_id := cloud_devs[dev_id].get(CONF_NODE_ID):
                    new_data[CONF_DEVICES][dev_id][CONF_NODE_ID] = new_node_id

                # Update Gateway ID and IP
                if new_gw := get_gateway_by_deviceid(dev_id, cloud_devs):
                    self.info(f"Gateway ID has been updated to: {new_gw.id}")
                    new_data[CONF_DEVICES][dev_id][CONF_GATEWAY_ID] = new_gw.id

                    if discovery and (local_gw := discovery.devices.get(new_gw.id)):
                        new_ip = local_gw.get(CONF_TUYA_IP, self._device_config.host)
                        new_data[CONF_DEVICES][dev_id][CONF_HOST] = new_ip
                        self.info(f"IP has been updated to: {new_ip}")

            new_data[CONF_DEVICES][dev_id][CONF_LOCAL_KEY] = self._local_key
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            self._hass.config_entries.async_update_entry(self._entry, data=new_data)
            self.info(f"Local-key has been updated")

    async def set_status(self):
        """Send self._pending_status payload to device."""
        await self.check_connection()
        if self._interface and self._pending_status:
            payload, self._pending_status = self._pending_status.copy(), {}
            try:
                await self._interface.set_dps(payload, cid=self._node_id)
            except Exception as ex:  # pylint: disable=broad-except
                self.debug(f"Failed to set values {payload} --> {ex}", force=True)
        elif not self._interface:
            self.error(f"Device is not connected.")

    async def set_dp(self, state, dp_index):
        """Change value of a DP of the Tuya device."""
        if self._interface is not None:
            self._pending_status.update({dp_index: state})
            await asyncio.sleep(0.001)
            await self.set_status()
        else:
            if self.is_sleep:
                return self._pending_status.update({str(dp_index): state})

    async def set_dps(self, states):
        """Change value of a DPs of the Tuya device."""
        if self._interface is not None:
            self._pending_status.update(states)
            await asyncio.sleep(0.001)
            await self.set_status()
        else:
            if self.is_sleep:
                return self._pending_status.update(states)

    async def _async_refresh(self, _now):
        if self.connected:
            self.debug("Refreshing dps for device")
            # This a workdaround for >= 3.4 devices, since there is an issue on waiting for the correct seqno
            try:
                await self._interface.update_dps(cid=self._node_id)
            except TimeoutError:
                pass

    def _dispatch_status(self):
        signal = f"localtuya_{self._device_config.id}"
        dispatcher_send(self._hass, signal, self._status)

    def _handle_event(self, old_status: dict, new_status: dict, deviceID=None):
        """Handle events in HA when devices updated."""

        def fire_event(event, data: dict):
            event_data = {CONF_DEVICE_ID: deviceID or self._device_config.id}
            event_data.update(data.copy())
            # Send an event with status, The default length of event without data is 2.
            if len(event_data) > 1:
                self._hass.bus.async_fire(f"localtuya_{event}", event_data)

        event = "states_update"
        device_triggered = "device_triggered"
        device_dp_triggered = "device_dp_triggered"

        # Device Initializing. if not old_states.
        # States update event.
        if old_status and old_status != new_status:
            data = {"old_states": old_status, "new_states": new_status}
            fire_event(event, data)

        # Device triggered event.
        if old_status and new_status is not None:
            event = device_triggered
            data = {"states": new_status}
            fire_event(event, data)

            if self._interface is not None:
                if len(self._interface.dispatched_dps) == 1:
                    event = device_dp_triggered
                    dpid_trigger = list(self._interface.dispatched_dps)[0]
                    dpid_value = self._interface.dispatched_dps.get(dpid_trigger)
                    data = {"dp": dpid_trigger, "value": dpid_value}
                    fire_event(event, data)

    def _shutdown_entities(self, now=None, exc=""):
        """Shutdown device entities"""
        if self.is_sleep or self.connected:
            return

        signal = f"localtuya_{self._device_config.id}"
        dispatcher_send(self._hass, signal, None)

        if self._is_closing:
            return

        if self.is_subdevice:
            self.info(f"Sub-device disconnected due to: {exc}")
        elif hasattr(self, "low_power"):
            m, s = divmod((int(time.time()) - self._last_update_time), 60)
            h, m = divmod(m, 60)
            self.info(f"The device is still out of reach since: {h}h:{m}m:{s}s")
        else:
            self.info(f"Disconnected due to: {exc}")

    @callback
    def status_updated(self, status: dict):
        """Device updated status."""
        if self._fake_gateway:
            # Fake gateways are only used to pass commands no need to update status.
            return
        self._last_update_time = int(time.time())

        self._handle_event(self._status, status)
        self._status.update(status)
        self._dispatch_status()

    @callback
    def disconnected(self, exc=""):
        """Device disconnected."""
        sleep_time = self._device_config.sleep_time

        self._interface = None

        if self._unsub_refresh:
            self._unsub_refresh()

        if self.sub_devices:
            for sub_dev in self.sub_devices.values():
                sub_dev.disconnected("Gateway disconnected")

        if self._connect_task is not None:
            self._connect_task.cancel("Device disconnected")
            self._connect_task = None

        # If it disconnects unexpectedly.
        if self._is_closing:
            return

        self._call_on_close.append(asyncio.create_task(self._async_reconnect()).cancel)
        delay = (0 if self.is_subdevice else 3) + sleep_time
        fun = partial(self._shutdown_entities, exc=exc)
        self._call_on_close.append(async_call_later(self._hass, delay, fun))

    async def _async_reconnect(self):
        """Task: continuously attempt to reconnect to the device."""
        if self._reconnect_task:
            return

        self._reconnect_task = True
        attempts = 0
        while True and not self._is_closing:
            # for sub-devices, if the gateway isn't connected then no need for reconnect.
            if self._gateway and (
                not self._gateway.connected or self._gateway.is_connecting
            ):
                await asyncio.sleep(3)
                continue

            try:
                if self._connect_task:
                    await self._connect_task
                else:
                    await self.async_connect()
            except asyncio.CancelledError as e:
                self.debug(f"Reconnect task has been canceled: {e}", force=True)
                break

            if self.connected:
                self.debug(f"Reconnect succeeded on attempt: {attempts}", force=True)
                break

            attempts += 1
            await asyncio.sleep(RECONNECT_INTERVAL.total_seconds())

        self._reconnect_task = False
