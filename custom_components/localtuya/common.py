"""Code shared between all platforms."""
import asyncio
import logging
import time
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_ID,
    CONF_PLATFORM,
    CONF_SCAN_INTERVAL,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from . import pytuya
from .const import (
    ATTR_UPDATED_AT,
    CONF_LOCAL_KEY,
    CONF_MODEL,
    CONF_PROTOCOL_VERSION,
<<<<<<< HEAD
    CONF_IS_GATEWAY,
    CONF_PARENT_GATEWAY,
    DOMAIN,
    GW_REQ_ADD,
    GW_REQ_REMOVE,
    GW_REQ_STATUS,
    GW_REQ_SET_DP,
    GW_REQ_SET_DPS,
    GW_EVT_STATUS_UPDATED,
    GW_EVT_CONNECTED,
    GW_EVT_DISCONNECTED,
    SUB_DEVICE_RECONNECT_INTERVAL,
    TUYA_DEVICE,
=======
    DATA_CLOUD,
    DOMAIN,
    TUYA_DEVICES,
<<<<<<< HEAD
>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b
=======
    CONF_DEFAULT_VALUE,
    ATTR_STATE,
    CONF_RESTORE_ON_RECONNECT,
    CONF_RESET_DPIDS,
>>>>>>> pr/4
)

_LOGGER = logging.getLogger(__name__)


def prepare_setup_entities(hass, config_entry, platform):
    """Prepare ro setup entities for a platform."""
    entities_to_setup = [
        entity
        for entity in config_entry.data[CONF_ENTITIES]
        if entity[CONF_PLATFORM] == platform
    ]
    if not entities_to_setup:
        return None, None

    tuyainterface = []

    return tuyainterface, entities_to_setup


async def async_setup_entry(
    domain: str,
    entity_class: type,
    flow_schema,
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up a Tuya platform based on a config entry.

    This is a generic method and each platform should lock domain and
    entity_class with functools.partial.
    """
<<<<<<< HEAD
    tuyainterface, entities_to_setup = prepare_setup_entities(
        hass, config_entry, domain
    )

    if not entities_to_setup:
        return
    dps_config_fields = list(get_dps_for_platform(flow_schema))

    for device_config in entities_to_setup:
        # Add DPS used by this platform to the request list
        for dp_conf in dps_config_fields:
            if dp_conf in device_config:
                tuyainterface.dps_to_request[device_config[dp_conf]] = None
        async_add_entities(
            [
                entity_class(
                    tuyainterface,
                    config_entry,
                    device_config[CONF_ID],
                )
            ],
            True,
        )

=======
    entities = []

    for dev_id in config_entry.data[CONF_DEVICES]:
        # entities_to_setup = prepare_setup_entities(
        #     hass, config_entry.data[dev_id], domain
        # )
        dev_entry = config_entry.data[CONF_DEVICES][dev_id]
        entities_to_setup = [
            entity
            for entity in dev_entry[CONF_ENTITIES]
            if entity[CONF_PLATFORM] == domain
        ]

        if entities_to_setup:

            tuyainterface = hass.data[DOMAIN][TUYA_DEVICES][dev_id]

            dps_config_fields = list(get_dps_for_platform(flow_schema))

            for entity_config in entities_to_setup:
                # Add DPS used by this platform to the request list
                for dp_conf in dps_config_fields:
                    if dp_conf in entity_config:
                        tuyainterface.dps_to_request[entity_config[dp_conf]] = None

                entities.append(
                    entity_class(
                        tuyainterface,
                        dev_entry,
                        entity_config[CONF_ID],
                    )
                )
    # Once the entities have been created, add to the TuyaDevice instance
    tuyainterface.add_entities(entities)
    async_add_entities(entities)

>>>>>>> 54dbc3a3591bb47b6d8fe3c1b3038489e2ba8d5b

def get_dps_for_platform(flow_schema):
    """Return config keys for all platform keys that depends on a datapoint."""
    for key, value in flow_schema(None).items():
        if hasattr(value, "container") and value.container is None:
            yield key.schema


def get_entity_config(config_entry, dp_id):
    """Return entity config for a given DPS id."""
    for entity in config_entry[CONF_ENTITIES]:
        if entity[CONF_ID] == dp_id:
            return entity
    raise Exception(f"missing entity config for id {dp_id}")


@callback
def async_config_entry_by_device_id(hass, device_id):
    """Look up config entry by device id."""
    current_entries = hass.config_entries.async_entries(DOMAIN)
    for entry in current_entries:
        if device_id in entry.data[CONF_DEVICES]:
            return entry
    return None


class TuyaDevice(pytuya.TuyaListener, pytuya.ContextualLogger):
    """Cache wrapper for pytuya.TuyaInterface."""

    def __init__(self, hass, config_entry, dev_id):
        """Initialize the cache."""
        super().__init__()
        self._hass = hass
        self._config_entry = config_entry
        self._dev_config_entry = config_entry.data[CONF_DEVICES][dev_id].copy()
        self._interface = None
        self._status = {}
        self.dps_to_request = {}
        self._is_closing = False
        self._connect_task = None
        self._disconnect_task = None
        self._unsub_interval = None
        self._entities = []
        self._local_key = self._dev_config_entry[CONF_LOCAL_KEY]
        self._default_reset_dpids = None
        if CONF_RESET_DPIDS in self._dev_config_entry:
            reset_ids_str = self._dev_config_entry[CONF_RESET_DPIDS].split(",")

            self._default_reset_dpids = []
            for reset_id in reset_ids_str:
                self._default_reset_dpids.append(int(reset_id.strip()))

        self.set_logger(_LOGGER, self._dev_config_entry[CONF_DEVICE_ID])

        # This has to be done in case the device type is type_0d
        for entity in self._dev_config_entry[CONF_ENTITIES]:
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

    def async_connect(self):
        """Connect to device if not already connected."""
        if not self._is_closing and self._connect_task is None and not self._interface:
            self._connect_task = asyncio.create_task(self._make_connection())

    async def _make_connection(self):
        """Subscribe localtuya entity events."""
        self.debug("Connecting to %s", self._dev_config_entry[CONF_HOST])

        try:
            self._interface = await pytuya.connect(
                self._dev_config_entry[CONF_HOST],
                self._dev_config_entry[CONF_DEVICE_ID],
                self._local_key,
                float(self._dev_config_entry[CONF_PROTOCOL_VERSION]),
                self,
            )

            self._interface.add_dps_to_request(self.dps_to_request)
        except Exception:  # pylint: disable=broad-except
            self.exception(f"Connect to {self._dev_config_entry[CONF_HOST]} failed")
            if self._interface is not None:
                await self._interface.close()
                self._interface = None

        if self._interface is not None:
            try:
                self.debug("Retrieving initial state")
                status = await self._interface.status()
                if status is None:
                    raise Exception("Failed to retrieve status")

                self._interface.start_heartbeat()
                self.status_updated(status)

            except Exception as ex:  # pylint: disable=broad-except
                try:
                    self.debug(
                        "Initial state update failed, trying reset command "
                        + "for DP IDs: %s",
                        self._default_reset_dpids,
                    )
                    await self._interface.reset(self._default_reset_dpids)

                    self.debug("Update completed, retrying initial state")
                    status = await self._interface.status()
                    if status is None or not status:
                        raise Exception("Failed to retrieve status") from ex

                    self._interface.start_heartbeat()
                    self.status_updated(status)

                except UnicodeDecodeError as e:  # pylint: disable=broad-except
                    self.exception(
                        f"Connect to {self._dev_config_entry[CONF_HOST]} failed: %s",
                        type(e),
                    )
                    if self._interface is not None:
                        await self._interface.close()
                        self._interface = None

                except Exception as e:  # pylint: disable=broad-except
                    self.exception(
                        f"Connect to {self._dev_config_entry[CONF_HOST]} failed"
                    )
                    if "json.decode" in str(type(e)):
                        await self.update_local_key()

                    if self._interface is not None:
                        await self._interface.close()
                        self._interface = None

        if self._interface is not None:
            # Attempt to restore status for all entities that need to first set
            # the DPS value before the device will respond with status.
            for entity in self._entities:
                await entity.restore_state_when_connected()

            if self._disconnect_task is not None:
                self._disconnect_task()

            def _new_entity_handler(entity_id):
                self.debug(
                    "New entity %s was added to %s",
                    entity_id,
                    self._dev_config_entry[CONF_HOST],
                )
                self._dispatch_status()

            signal = f"localtuya_entity_{self._dev_config_entry[CONF_DEVICE_ID]}"
            self._disconnect_task = async_dispatcher_connect(
                self._hass, signal, _new_entity_handler
            )

            if (
                CONF_SCAN_INTERVAL in self._dev_config_entry
                and self._dev_config_entry[CONF_SCAN_INTERVAL] > 0
            ):
                self._unsub_interval = async_track_time_interval(
                    self._hass,
                    self._async_refresh,
                    timedelta(seconds=self._dev_config_entry[CONF_SCAN_INTERVAL]),
                )

        self._connect_task = None

    async def update_local_key(self):
        """Retrieve updated local_key from Cloud API and update the config_entry."""
        dev_id = self._dev_config_entry[CONF_DEVICE_ID]
        await self._hass.data[DOMAIN][DATA_CLOUD].async_get_devices_list()
        cloud_devs = self._hass.data[DOMAIN][DATA_CLOUD].device_list
        if dev_id in cloud_devs:
            self._local_key = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
            new_data = self._config_entry.data.copy()
            new_data[CONF_DEVICES][dev_id][CONF_LOCAL_KEY] = self._local_key
            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            self._hass.config_entries.async_update_entry(
                self._config_entry,
                data=new_data,
            )
            self.info("local_key updated for device %s.", dev_id)

    async def _async_refresh(self, _now):
        if self._interface is not None:
            await self._interface.update_dps()

    async def close(self):
        """Close connection and stop re-connect loop."""
        self._is_closing = True
        if self._connect_task is not None:
            self._connect_task.cancel()
            await self._connect_task
        if self._interface is not None:
            await self._interface.close()
        if self._disconnect_task is not None:
            self._disconnect_task()
        self.debug(
            "Closed connection with device %s.",
            self._dev_config_entry[CONF_FRIENDLY_NAME],
        )

    async def set_dp(self, state, dp_index):
        """Change value of a DP of the Tuya device."""
        if self._interface is not None:
            try:
                await self._interface.set_dp(state, dp_index)
            except Exception:  # pylint: disable=broad-except
                self.exception("Failed to set DP %d to %s", dp_index, str(state))
        else:
            self.error(
                "Not connected to device %s", self._dev_config_entry[CONF_FRIENDLY_NAME]
            )

    async def set_dps(self, states):
        """Change value of a DPs of the Tuya device."""
        if self._interface is not None:
            try:
                await self._interface.set_dps(states)
            except Exception:  # pylint: disable=broad-except
                self.exception("Failed to set DPs %r", states)
        else:
            self.error(
                "Not connected to device %s", self._dev_config_entry[CONF_FRIENDLY_NAME]
            )

    @callback
    def status_updated(self, status):
        """Device updated status."""
        self._status.update(status)
        self._dispatch_status()

    def _dispatch_status(self):
        signal = f"localtuya_{self._dev_config_entry[CONF_DEVICE_ID]}"
        async_dispatcher_send(self._hass, signal, self._status)

    @callback
    def disconnected(self):
        """Device disconnected."""
        signal = f"localtuya_{self._dev_config_entry[CONF_DEVICE_ID]}"
        async_dispatcher_send(self._hass, signal, None)
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
        self._interface = None
        self.debug("Disconnected - waiting for discovery broadcast")


class TuyaGatewayDevice(pytuya.TuyaListener, pytuya.ContextualLogger):
    """Gateway wrapper for pytuya.TuyaInterface."""

    def __init__(self, hass, config_entry):
        """Initialize the cache."""
        super().__init__()
        self._hass = hass
        self._config_entry = config_entry
        self._interface = None
        self._is_closing = False
        # Tuya Gateway needs to be connected first before sub-devices start connecting
        self._connect_task = asyncio.create_task(self._make_connection())
        self._sub_device_task = None
        self._retry_sub_conn_interval = None
        self._sub_devices = {}
        self.set_logger(_LOGGER, config_entry[CONF_DEVICE_ID])

        # Safety check
        if not config_entry.get(CONF_IS_GATEWAY):
            raise Exception("Device {0} is not a gateway but using TuyaGatewayDevice!", config_entry[CONF_DEVICE_ID])

    @property
    def connected(self):
        """Return if connected to device."""
        return self._interface is not None

    def async_connect(self):
        """Connect to device if not already connected."""
        if not self._is_closing and self._connect_task is None and not self._interface:
            self._connect_task = asyncio.create_task(self._make_connection())

    async def _make_connection(self):
        """Subscribe localtuya entity events."""
        self.debug("Connecting to gateway %s", self._config_entry[CONF_HOST])

        if not self._sub_device_task:
            signal = f"localtuya_gateway_{self._config_entry[CONF_DEVICE_ID]}"
            self._sub_device_task = async_dispatcher_connect(
                self._hass, signal, self._handle_sub_device_request
        )

        try:
            self._interface = await pytuya.connect(
                self._config_entry[CONF_HOST],
                self._config_entry[CONF_DEVICE_ID],
                self._config_entry[CONF_LOCAL_KEY],
                float(self._config_entry[CONF_PROTOCOL_VERSION]),
                self,
                is_gateway=True,
            )

            # Re-add and get status of previously added sub-devices
            # Note this assumes the gateway device has not been tear down
            for cid in self._sub_devices:
                self._add_sub_device_interface(cid, self._sub_devices[cid]["dps"])
                self._dispatch_event(GW_EVT_CONNECTED, None, cid)

                # Initial status update
                await self._get_sub_device_status(cid, False)

            self._retry_sub_conn_interval = async_track_time_interval(
                self._hass,
                self._retry_sub_device_connection,
                timedelta(seconds=SUB_DEVICE_RECONNECT_INTERVAL),
            )

        except Exception:  # pylint: disable=broad-except
            self.exception(f"Connect to gateway {self._config_entry[CONF_HOST]} failed")
            if self._interface is not None:
                await self._interface.close()
                self._interface = None
        self._connect_task = None

    async def _handle_sub_device_request(self, data):
        """Handles a request dispatched from a sub-device"""
        request = data["request"]
        cid = data["cid"]
        content = data["content"]

        self.debug("Received request %s from %s with content %s", request, cid, content)

        if request == GW_REQ_ADD:
            if cid in self._sub_devices:
                self.warning("Duplicate sub-device addition for %s", cid)
            else:
                self._sub_devices[cid] = {"dps": content["dps"], "retry_status": False}
                self._add_sub_device_interface(cid, content["dps"])
                self._dispatch_event(GW_EVT_CONNECTED, None, cid)
                # Initial status update
                await self._get_sub_device_status(cid, False)
        elif request == GW_REQ_REMOVE:
            if cid not in self._sub_devices:
                self.warning("Invalid sub-device removal request for %s", cid)
            else:
                del self._sub_devices[cid]
                if self._interface is not None:
                    self._interface.remove_sub_device(cid)
                self._dispatch_event(GW_EVT_DISCONNECTED, None, cid)
        elif request == GW_REQ_STATUS:
            await self._get_sub_device_status(cid, False)
        elif request == GW_REQ_SET_DP:
            if self._interface is not None:
                await self._interface.set_dp(content["value"], content["dp_index"], cid)
        elif request == GW_REQ_SET_DPS:
            if self._interface is not None:
                await self._interface.set_dps(content["dps"], cid)
        else:
            self.debug("Invalid request %s from %s", request, cid)

    def _add_sub_device_interface(self, cid, dps):
        """Adds a sub-device to underlying pytuya interface"""
        if self._interface is not None:
            self._interface.add_sub_device(cid)
            self._interface.add_dps_to_request(dps, cid)

    async def _get_sub_device_status(self, cid, is_retry):
        """
        Queries sub-device status and dispatch events depending on if it's a retry.
        Retries are used because we have no way of knowing if a sub-device has disconnected,
            therefore we consistently query failed status updates to know if a device comes
            back online.
        """
        if self._interface is not None:
            status = await self._interface.status(cid)
        else:
            status = None

        if status:
            self.status_updated(status)
            self._sub_devices[cid]["retry_status"] = False
            # Commented out by knifehandz 2022/02/13
            # Skip updating connection based on status updates for now
            #
            # if is_retry:
            #     self._dispatch_event(GW_EVT_CONNECTED, None, cid)
        else:
            # Special case to ask sub-device to use its last cached status
            self._dispatch_event(GW_EVT_STATUS_UPDATED, {"use_last_status": True}, cid)
            self._sub_devices[cid]["retry_status"] = True
            # Skip updating connection based on status updates for now
            #
            # if not is_retry:
            #     self._dispatch_event(GW_EVT_DISCONNECTED, None, cid)

    def _dispatch_event(self, event, event_data, cid):
        """Dispatches an event to a sub-device"""
        self.debug("Dispatching event %s to sub-device %s with data %s", event, cid, event_data)

        async_dispatcher_send(
            self._hass,
            f"localtuya_subdevice_{cid}",
            {
                "event": event,
                "event_data": event_data
            }
        )

    async def _retry_sub_device_connection(self, _now):
        """ Retries sub-device status, to be called by a HASS interval """
        for cid in self._sub_devices:
            if self._sub_devices[cid]["retry_status"]:
                await self._get_sub_device_status(cid, True)

    async def close(self):
        """Close connection and stop re-connect loop."""
        self._is_closing = True
        if self._connect_task is not None:
            self._connect_task.cancel()
            await self._connect_task
        if self._sub_device_task is not None:
            self._sub_device_task()
        if self._interface is not None:
            await self._interface.close()

    @callback
    def status_updated(self, status):
        """Device updated status."""
        cid = status["last_updated_cid"]
        if cid == "":  # Not a status update we are interested in
            return

        self._dispatch_event(GW_EVT_STATUS_UPDATED, status[cid], cid)

    @callback
    def disconnected(self):
        """Device disconnected."""
        if self._retry_sub_conn_interval is not None:
            self._retry_sub_conn_interval()
            self._retry_sub_conn_interval = None

        for cid in self._sub_devices:
            self._dispatch_event(GW_EVT_DISCONNECTED, None, cid)

        self._interface = None
        self.debug("Disconnected - waiting for discovery broadcast")


class TuyaSubDevice(pytuya.TuyaListener, pytuya.ContextualLogger):
    """Cache wrapper for a sub-device under a gateway."""

    def __init__(self, hass, config_entry):
        """Initialize the cache."""
        super().__init__()
        self._hass = hass
        self._config_entry = config_entry
        self._parent_gateway = config_entry.get(CONF_PARENT_GATEWAY)
        self._status = {}
        self.dps_to_request = {}
        self._device_disconnect_task = None
        self._entity_disconnect_task = None
        self._is_closing = False
        self._is_connected = False
        self._is_added = False
        self.set_logger(_LOGGER, config_entry[CONF_DEVICE_ID])

        # Safety check
        if not config_entry.get(CONF_PARENT_GATEWAY):
            raise Exception("Device {0} is not a sub-device but using TuyaSubDevice!", config_entry[CONF_DEVICE_ID])

        # Populate dps list from entities
        for entity in config_entry[CONF_ENTITIES]:
            self.dps_to_request[entity[CONF_ID]] = None

    @property
    def connected(self):
        """Return if connected to device."""
        return self._is_connected

    def async_connect(self):
        """Add device if not added."""
        if not self._is_added and not self._is_closing:
            self.debug(
                "Connecting to sub-device %s via %s",
                self._config_entry[CONF_DEVICE_ID],
                self._parent_gateway,
            )

            signal = f"localtuya_subdevice_{self._config_entry[CONF_DEVICE_ID]}"
            self._device_disconnect_task = async_dispatcher_connect(
                self._hass, signal, self._handle_gateway_event
            )

            def _new_entity_handler(entity_id):
                self.debug(
                    "New entity %s was added to %s",
                    entity_id,
                    self._config_entry[CONF_DEVICE_ID],
                )
                self._dispatch_status()

            signal = f"localtuya_entity_{self._config_entry[CONF_DEVICE_ID]}"
            self._entity_disconnect_task = async_dispatcher_connect(
                self._hass, signal, _new_entity_handler
            )

            self._async_dispatch_gateway_request(GW_REQ_ADD, {
                "dps": self.dps_to_request
            })

            self._is_added = True

    def _handle_gateway_event(self, data):
        """Handle events from gateway"""
        event = data["event"]
        event_data = data["event_data"]

        self.debug("Received event %s from gateway with data %s", event, event_data)

        if event == GW_EVT_STATUS_UPDATED:
            self.status_updated(event_data)
        elif event == GW_EVT_CONNECTED:
            self._is_connected = True
        elif event == GW_EVT_DISCONNECTED:
            self.disconnected()
        else:
            self.debug("Invalid event %s from gateway", event)

    def _async_dispatch_gateway_request(self, request, content):
        """Dispatches a request to the parent gateway using a retry loop"""
        self.debug("Dispatching request %s to gateway with content %s", request, content)

        async_dispatcher_send(
            self._hass,
            f"localtuya_gateway_{self._parent_gateway}",
            {
                "request": request,
                "cid": self._config_entry[CONF_DEVICE_ID],
                "content": content,
            },
        )

    async def set_dp(self, state, dp_index):
        """Change value of a DP of the Tuya device."""
        if self._is_connected:
            self._async_dispatch_gateway_request(GW_REQ_SET_DP, {
                "value": state,
                "dp_index": dp_index,
            })
        else:
            self.error(
                "Not connected to device %s", self._config_entry[CONF_FRIENDLY_NAME]
            )

    async def set_dps(self, states):
        """Change value of DPs of the Tuya device."""
        if self._is_connected:
            self._async_dispatch_gateway_request(GW_REQ_SET_DPS, {
                "dps": states,
            })
        else:
            self.error(
                "Not connected to device %s", self._config_entry[CONF_FRIENDLY_NAME]
            )

    async def close(self):
        """Close connection and stop re-connect loop."""
        self._is_closing = True
        self._async_dispatch_gateway_request(GW_REQ_REMOVE, None)
        self._is_added = False
        if self._device_disconnect_task is not None:
            self._device_disconnect_task()
        if self._entity_disconnect_task is not None:
            self._entity_disconnect_task()

    @callback
    def status_updated(self, status):
        """Device updated status."""
        if not status.get("use_last_status"):
            self._status.update(status)
        self._dispatch_status()

    def _dispatch_status(self):
        """Dispatches status to downstream entities"""
        signal = f"localtuya_{self._config_entry[CONF_DEVICE_ID]}"
        async_dispatcher_send(self._hass, signal, self._status)

    @callback
    def disconnected(self):
        """Device disconnected."""
        self._is_connected = False
        signal = f"localtuya_{self._config_entry[CONF_DEVICE_ID]}"
        async_dispatcher_send(self._hass, signal, None)

        self.debug("Disconnected")


class LocalTuyaEntity(RestoreEntity, pytuya.ContextualLogger):
    """Representation of a Tuya entity."""

    def __init__(self, device, config_entry, dp_id, logger, **kwargs):
        """Initialize the Tuya entity."""
        super().__init__()
        self._device = device
        self._dev_config_entry = config_entry
        self._config = get_entity_config(config_entry, dp_id)
        self._dp_id = dp_id
        self._status = {}
        self._state = None
        self._last_state = None

        # Default value is available to be provided by Platform entities if required
        self._default_value = self._config.get(CONF_DEFAULT_VALUE)

        """ Restore on connect setting is available to be provided by Platform entities
        if required"""
        self._restore_on_reconnect = (
            self._config.get(CONF_RESTORE_ON_RECONNECT) or False
        )
        self.set_logger(logger, self._dev_config_entry[CONF_DEVICE_ID])

    async def async_added_to_hass(self):
        """Subscribe localtuya events."""
        await super().async_added_to_hass()

        self.debug("Adding %s with configuration: %s", self.entity_id, self._config)

        state = await self.async_get_last_state()
        if state:
            self.status_restored(state)

        def _update_handler(status):
            """Update entity state when status was updated."""
            update = False

            if status is None:
                self._status = {}
                update = True
            elif self._status != status and str(self._dp_id) in status:
                self._status = status.copy()
<<<<<<< HEAD
                update = True

            if update:
                self.status_updated()
=======
                if status:
                    self.status_updated()

                # Update HA
>>>>>>> pr/4
                self.schedule_update_ha_state()

        signal = f"localtuya_{self._dev_config_entry[CONF_DEVICE_ID]}"

        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, _update_handler)
        )

        signal = f"localtuya_entity_{self._dev_config_entry[CONF_DEVICE_ID]}"
        async_dispatcher_send(self.hass, signal, self.entity_id)

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes to be saved.

        These attributes are then available for restore when the
        entity is restored at startup.
        """
        attributes = {}
        if self._state is not None:
            attributes[ATTR_STATE] = self._state
        elif self._last_state is not None:
            attributes[ATTR_STATE] = self._last_state

        self.debug("Entity %s - Additional attributes: %s", self.name, attributes)
        return attributes

    @property
    def device_info(self):
        """Return device information for the device registry."""
        model = self._dev_config_entry.get(CONF_MODEL, "Tuya generic")
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"local_{self._dev_config_entry[CONF_DEVICE_ID]}")
            },
            "name": self._dev_config_entry[CONF_FRIENDLY_NAME],
            "manufacturer": "Tuya",
            "model": f"{model} ({self._dev_config_entry[CONF_DEVICE_ID]})",
            "sw_version": self._dev_config_entry[CONF_PROTOCOL_VERSION],
        }

    @property
    def name(self):
        """Get name of Tuya entity."""
        return self._config[CONF_FRIENDLY_NAME]

    @property
    def should_poll(self):
        """Return if platform should poll for updates."""
        return False

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"local_{self._dev_config_entry[CONF_DEVICE_ID]}_{self._dp_id}"

    def has_config(self, attr):
        """Return if a config parameter has a valid value."""
        value = self._config.get(attr, "-1")
        return value is not None and value != "-1"

    @property
    def available(self):
        """Return if device is available or not."""
        return str(self._dp_id) in self._status

    def dps(self, dp_index):
        """Return cached value for DPS index."""
        value = self._status.get(str(dp_index))
        if value is None:
            self.warning(
                "Entity %s is requesting unknown DPS index %s",
                self.entity_id,
                dp_index,
            )

        return value

    def dps_conf(self, conf_item):
        """Return value of datapoint for user specified config item.

        This method looks up which DP a certain config item uses based on
        user configuration and returns its value.
        """
        dp_index = self._config.get(conf_item)
        if dp_index is None:
            self.warning(
                "Entity %s is requesting unset index for option %s",
                self.entity_id,
                conf_item,
            )
        return self.dps(dp_index)

    def status_updated(self):
        """Device status was updated.

        Override in subclasses and update entity specific state.
        """
        state = self.dps(self._dp_id)
        self._state = state

        # Keep record in last_state as long as not during connection/re-connection,
        # as last state will be used to restore the previous state
        if (state is not None) and (not self._device.is_connecting):
            self._last_state = state

    def status_restored(self, stored_state):
        """Device status was restored.

        Override in subclasses and update entity specific state.
        """
        raw_state = stored_state.attributes.get(ATTR_STATE)
        if raw_state is not None:
            self._last_state = raw_state
            self.debug(
                "Restoring state for entity: %s - state: %s",
                self.name,
                str(self._last_state),
            )

    def default_value(self):
        """Return default value of this entity.

        Override in subclasses to specify the default value for the entity.
        """
        # Check if default value has been set - if not, default to the entity defaults.
        if self._default_value is None:
            self._default_value = self.entity_default_value()

        return self._default_value

    def entity_default_value(self):  # pylint: disable=no-self-use
        """Return default value of the entity type.

        Override in subclasses to specify the default value for the entity.
        """
        return 0

    @property
    def restore_on_reconnect(self):
        """Return whether the last state should be restored on a reconnect.

        Useful where the device loses settings if powered off
        """
        return self._restore_on_reconnect

    async def restore_state_when_connected(self):
        """Restore if restore_on_reconnect is set, or if no status has been yet found.

        Which indicates a DPS that needs to be set before it starts returning
        status.
        """
        if not self.restore_on_reconnect and (str(self._dp_id) in self._status):
            self.debug(
                "Entity %s (DP %d) - Not restoring as restore on reconnect is  \
                disabled for this entity and the entity has an initial status",
                self.name,
                self._dp_id,
            )
            return

        self.debug("Attempting to restore state for entity: %s", self.name)
        # Attempt to restore the current state - in case reset.
        restore_state = self._state

        # If no state stored in the entity currently, go from last saved state
        if (restore_state == STATE_UNKNOWN) | (restore_state is None):
            self.debug("No current state for entity")
            restore_state = self._last_state

        # If no current or saved state, then use the default value
        if restore_state is None:
            self.debug("No last restored state - using default")
            restore_state = self.default_value()

        self.debug(
            "Entity %s (DP %d) - Restoring state: %s",
            self.name,
            self._dp_id,
            str(restore_state),
        )

        # Manually initialise
        await self._device.set_dp(restore_state, self._dp_id)
