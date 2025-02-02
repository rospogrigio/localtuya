"""Tuya Device API"""

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Callable, Coroutine, NamedTuple


from homeassistant.core import HomeAssistant, CALLBACK_TYPE, callback, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_DEVICES, CONF_HOST, CONF_DEVICE_ID
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
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
RESTORE_STATES = {"0": "restore"}


async def async_setup_entry(
    domain,
    entity_class,
    flow_schema,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up a Tuya platform based on a config entry.

    This is a generic method and each platform should lock domain and
    entity_class with functools.partial.
    """
    entities = []
    hass_entry_data: HassLocalTuyaData = hass.data[DOMAIN][config_entry.entry_id]

    for dev_id in config_entry.data[CONF_DEVICES]:
        dev_entry: dict = config_entry.data[CONF_DEVICES][dev_id]

        host = dev_entry.get(CONF_HOST)
        node_id = dev_entry.get(CONF_NODE_ID)
        device_key = f"{host}_{node_id}" if node_id else host

        if device_key not in hass_entry_data.devices:
            continue

        entities_to_setup = [
            entity
            for entity in dev_entry[CONF_ENTITIES]
            if entity[CONF_PLATFORM] == domain
        ]

        if entities_to_setup:
            device: TuyaDevice = hass_entry_data.devices[device_key]
            dps_config_fields = list(get_dps_for_platform(flow_schema))

            for entity_config in entities_to_setup:
                # Add DPS used by this platform to the request list
                for dp_conf in dps_config_fields:
                    if dp_conf in entity_config:
                        device.dps_to_request[entity_config[dp_conf]] = None

                entities.append(
                    entity_class(
                        device,
                        dev_entry,
                        entity_config[CONF_ID],
                    )
                )
    # Once the entities have been created, add to the TuyaDevice instance
    device.add_entities(entities)
    async_add_entities(entities)


def get_dps_for_platform(flow_schema):
    """Return config keys for all platform keys that depends on a datapoint."""
    for key, value in flow_schema(None).items():
        if hasattr(value, "container") and value.container is None:
            yield key.schema


def get_entity_config(config_entry, dp_id) -> dict:
    """Return entity config for a given DPS id."""
    for entity in config_entry[CONF_ENTITIES]:
        if entity[CONF_ID] == dp_id:
            return entity
    raise Exception(f"missing entity config for id {dp_id}")


@callback
def async_config_entry_by_device_id(hass: HomeAssistant, device_id):
    """Look up config entry by device id."""
    current_entries = hass.config_entries.async_entries(DOMAIN)
    for entry in current_entries:
        if device_id in entry.data.get(CONF_DEVICES, []):
            return entry
        else:
            _LOGGER.debug(f"Missing device configuration for device_id {device_id}")
        # Search for gateway_id
        for dev_conf in entry.data[CONF_DEVICES].values():
            if (gw_id := dev_conf.get(CONF_GATEWAY_ID)) and gw_id == device_id:
                return entry
    return None


class TuyaDevice(pytuya.TuyaListener, pytuya.ContextualLogger):
    """Cache wrapper for pytuya.TuyaInterface."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_config: dict,
        fake_gateway=False,
    ):
        """Initialize the cache."""
        super().__init__()
        self._hass = hass
        self._hass_entry: HassLocalTuyaData = None
        self._config_entry = config_entry
        self._device_config = DeviceConfig(device_config.copy())

        self._interface = None
        self._connect_max_tries = 3

        # For SubDevices
        self._node_id: str = self._device_config.node_id
        self._fake_gateway = fake_gateway
        self._gwateway: TuyaDevice = None
        self._sub_devices: dict[str, TuyaDevice] = {}

        self._status = {}
        # Sleep timer, a device that reports the status every x seconds then goes into sleep.
        self._passive_device = self._device_config.sleep_time > 0
        self._last_update_time: int = int(time.time()) - 5
        self._pending_status: dict[str, dict[str, Any]] = {}

        self.dps_to_request = {}
        self._is_closing = False
        self._connect_task: asyncio.Task | None = None
        self._disconnect_task: Callable[[], None] | None = None
        self._unsub_interval: CALLBACK_TYPE[[], None] = None
        self._shutdown_entities_delay: CALLBACK_TYPE[[], None] = None
        self._entities = []
        self._local_key: str = self._device_config.local_key
        self._default_reset_dpids: list | None = None
        if reset_dps := self._device_config.reset_dps:
            self._default_reset_dpids = [int(id.strip()) for id in reset_dps.split(",")]

        self.set_logger(
            _LOGGER, self._device_config.id, self._device_config.enable_debug
        )

        # This has to be done in case the device type is type_0d
        for entity in self._device_config.entities:
            self.dps_to_request[entity[CONF_ID]] = None

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
        return self._interface is not None

    @property
    def is_subdevice(self):
        """Return whether this is a subdevice or not."""
        return self._node_id and not self._fake_gateway

    @property
    def is_sleep(self):
        """Return whether the device is sleep or not."""
        device_sleep = self._device_config.sleep_time
        last_update = int(time.time()) - self._last_update_time
        is_sleep = last_update < device_sleep

        return device_sleep > 0 and is_sleep

    async def get_gateway(self):
        """Return the gateway device of this sub device."""
        if not self._node_id:
            return
        gateway: TuyaDevice
        node_host = self._device_config.host
        devices: dict = self._hass_entry.devices

        # Sub to gateway.
        if gateway := devices.get(node_host):
            self._gwateway = gateway
            gateway._sub_devices[self._node_id] = self
            return gateway
        else:
            self.error(f"Couldn't find the gateway for: {self._node_id}")
        return None

    async def async_connect(self, _now=None) -> None:
        """Connect to device if not already connected."""
        if not self._hass_entry:
            self._hass_entry = self._hass.data[DOMAIN][self._config_entry.entry_id]

        if not self._is_closing and not self.is_connecting and not self.connected:
            try:
                self._connect_task = asyncio.create_task(self._make_connection())
                if not self.is_sleep:
                    await self._connect_task
            except (TimeoutError, asyncio.CancelledError):
                ...

    async def _make_connection(self):
        """Subscribe localtuya entity events."""
        if self.is_sleep and not self._status:
            self.status_updated(RESTORE_STATES)

        name = self._device_config.name
        host = name if self.is_subdevice else self._device_config.host
        retry = 0
        update_localkey = False

        self.debug(f"Trying to connect to {host}...", force=True)
        while retry < self._connect_max_tries:
            retry += 1
            try:
                if self.is_subdevice:
                    gateway = await self.get_gateway()
                    if not gateway or (not gateway.connected and gateway.is_connecting):
                        return await self.abort_connect()
                    self._interface = gateway._interface
                else:
                    self._interface = await asyncio.wait_for(
                        pytuya.connect(
                            self._device_config.host,
                            self._device_config.id,
                            self._local_key,
                            float(self._device_config.protocol_version),
                            self._device_config.enable_debug,
                            self,
                        ),
                        5,
                    )
                self._interface.add_dps_to_request(self.dps_to_request)
                break  # Succeed break while loop
            except Exception as ex:  # pylint: disable=broad-except
                await self.abort_connect()
                if not retry < self._connect_max_tries and not self.is_sleep:
                    self.warning(f"Failed to connect to {host}: {str(ex)}")
                if "key" in str(ex):
                    update_localkey = True
                    break

        if self._interface is not None:
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
                status = await self._interface.detect_available_dps(cid=self._node_id)
                if status is None:  # and not self.is_subdevice
                    raise Exception("Failed to retrieve status")
                self._interface.start_heartbeat()
                self.status_updated(status)

            except UnicodeDecodeError as e:
                self.exception(f"Connect to {host} failed: due to: {type(e)}")
                await self.abort_connect()
                update_localkey = True
            except pytuya.DecodeError as derror:
                self.info(f"Initial update state failed {derror}, trying key update")
                await self.abort_connect()
                update_localkey = True
            except Exception as e:
                if not (self._fake_gateway and "Not found" in str(e)):
                    e = "Sub device is not connected" if self.is_subdevice else e
                    self.warning(f"Connect to {host} failed: {e}")
                    await self.abort_connect()
                    update_localkey = True
            except:
                if self._fake_gateway:
                    self.warning(f"Failed to use {name} as gateway.")
                    await self.abort_connect()

        if self._interface is not None:
            # Attempt to restore status for all entities that need to first set
            # the DPS value before the device will respond with status.
            for entity in self._entities:
                await entity.restore_state_when_connected()

            def _new_entity_handler(entity_id):
                self.debug(f"New entity {entity_id} was added to {host}")
                self._dispatch_status()

            signal = f"localtuya_entity_{self._device_config.id}"
            self._disconnect_task = async_dispatcher_connect(
                self._hass, signal, _new_entity_handler
            )

            if (scan_inv := int(self._device_config.scan_interval)) > 0:
                self._unsub_interval = async_track_time_interval(
                    self._hass, self._async_refresh, timedelta(seconds=scan_inv)
                )

            self._connect_task = None
            self.debug(f"Success: connected to {host}", force=True)
            if self._sub_devices:
                connect_sub_devices = [
                    device.async_connect() for device in self._sub_devices.values()
                ]
                await asyncio.gather(*connect_sub_devices)

            if not self._status and "0" in self._device_config.manual_dps.split(","):
                self.status_updated(RESTORE_STATES)

            if self._pending_status:
                await self.set_dps(self._pending_status)
                self._pending_status = {}

        # If not connected try to handle the errors.
        if not self._interface:
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

        if not self.is_sleep:
            self._shutdown_entities()

    async def check_connection(self):
        """Ensure that the device is not still connecting; if it is, wait for it."""
        if not self.connected and self._connect_task:
            await self._connect_task
        if not self.connected and self._gwateway and self._gwateway._connect_task:
            await self._gwateway._connect_task
        if not self._interface:
            self.error(f"Not connected to device {self._device_config.name}")

    async def close(self):
        """Close connection and stop re-connect loop."""
        self._is_closing = True
        if self._shutdown_entities_delay is not None:
            self._shutdown_entities_delay()
        if self._connect_task is not None:
            self._connect_task.cancel()
            await self._connect_task
            self._connect_task = None
        if self._interface is not None:
            await self._interface.close()
            self._interface = None
        if self._disconnect_task:
            self._disconnect_task()
        self.debug(f"Closed connection with {self._device_config.name}", force=True)

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

            new_data = self._config_entry.data.copy()
            self._local_key = cloud_localkey

            if self._node_id:
                from .core.helpers import get_gateway_by_deviceid

                # Update Node ID.
                if new_node_id := cloud_devs[dev_id].get(CONF_NODE_ID):
                    new_data[CONF_DEVICES][dev_id][CONF_NODE_ID] = new_node_id

                # Update Gateway ID and IP
                if new_gw := get_gateway_by_deviceid(dev_id, cloud_devs):
                    new_data[CONF_DEVICES][dev_id][CONF_GATEWAY_ID] = new_gw.id
                    self.info(f"Updated {dev_id} gateway ID to: {new_gw.id}")
                    if discovery and (local_gw := discovery.devices.get(new_gw.id)):
                        new_ip = local_gw.get(CONF_TUYA_IP, self._device_config.host)
                        new_data[CONF_DEVICES][dev_id][CONF_HOST] = new_ip
                        self.info(f"Updated {dev_id} IP to: {new_ip}")

                self.info(f"Updated informations for sub-device {dev_id}.")

            new_data[CONF_DEVICES][dev_id][CONF_LOCAL_KEY] = self._local_key
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            self._hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            self.info(f"local_key updated for device {dev_id}.")

    async def set_values(self):
        """Send self._pending_status payload to device."""
        await self.check_connection()
        if self._interface and self._pending_status:
            payload, self._pending_status = self._pending_status.copy(), {}
            try:
                await self._interface.set_dps(payload, cid=self._node_id)
            except Exception:  # pylint: disable=broad-except
                self.debug(f"Failed to set values {payload}", force=True)
        elif not self._interface:
            self.error(f"Device is not connected.")

    async def set_dp(self, state, dp_index):
        """Change value of a DP of the Tuya device."""
        if self._interface is not None:
            self._pending_status.update({dp_index: state})
            await asyncio.sleep(0.01)
            await self.set_values()
        else:
            if self.is_sleep:
                return self._pending_status.update({str(dp_index): state})

    async def set_dps(self, states):
        """Change value of a DPs of the Tuya device."""
        if self._interface is not None:
            self._pending_status.update(states)
            await asyncio.sleep(0.01)
            await self.set_values()
        else:
            if self.is_sleep:
                return self._pending_status.update(states)

    async def _async_refresh(self, _now):
        if self._interface is not None:
            self.debug("Refreshing dps for device")
            await self._interface.update_dps(cid=self._node_id)

    def _dispatch_status(self):
        signal = f"localtuya_{self._device_config.id}"
        async_dispatcher_send(self._hass, signal, self._status)

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

    def _shutdown_entities(self, now=None):
        """Shutdown device entities"""
        self._shutdown_entities_delay = None
        if self.is_sleep:
            return
        if not self.connected:
            self.debug(f"Disconnected: waiting for discovery broadcast", force=True)
            signal = f"localtuya_{self._device_config.id}"
            async_dispatcher_send(self._hass, signal, None)

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
    def disconnected(self):
        """Device disconnected."""
        sleep_time = self._device_config.sleep_time

        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
        self._interface = None

        if self._sub_devices:
            for sub_dev in self._sub_devices.values():
                sub_dev.disconnected()

        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None

        # If it disconnects unexpectedly.
        if not self._is_closing and not self.is_subdevice:
            # Try quick reconnect.
            async_call_later(self._hass, 1, self.async_connect)

        if not self._is_closing:
            self._shutdown_entities_delay = async_call_later(
                self._hass, sleep_time + 3, self._shutdown_entities
            )


class HassLocalTuyaData(NamedTuple):
    """LocalTuya data stored in homeassistant data object."""

    cloud_data: TuyaCloudApi
    devices: dict[str, TuyaDevice]
    unsub_listeners: list[CALLBACK_TYPE,]
