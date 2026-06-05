"""Code shared between all platforms."""
import asyncio
import contextlib
import json.decoder
import logging
import time
from datetime import timedelta

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
    ATTR_STATE,
    ATTR_UPDATED_AT,
    CONF_DEFAULT_VALUE,
    CONF_ENABLE_DEBUG,
    CONF_LOCAL_KEY,
    CONF_MODEL,
    CONF_PASSIVE_ENTITY,
    CONF_PROTOCOL_VERSION,
    CONF_RESET_DPIDS,
    CONF_RESTORE_ON_RECONNECT,
    DATA_CLOUD,
    DOMAIN,
    TUYA_DEVICES,
)
from .host_resolver import (
    HostResolution,
    find_host_for_device_id,
    mac_from_device_id,
    scan_subnet_for_tuya_hosts,
)

_LOGGER = logging.getLogger(__name__)

_STATUS_UNCHANGED = object()
_RECONNECT_INITIAL_DELAY = 5
_RECONNECT_MAX_DELAY = 300
_HOST_RECOVERY_SCAN_FAILURES = 4
_HOST_RECOVERY_SCAN_INTERVAL = 900
_HOST_RECOVERY_PROBE_CONCURRENCY = 6
_HOST_RECOVERY_PROBE_TIMEOUT = 3
_CONNECT_FAILURE_WARNING_INTERVAL = 6 * 60 * 60


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
    domain, entity_class, flow_schema, hass, config_entry, async_add_entities
):
    """Set up a Tuya platform based on a config entry.

    This is a generic method and each platform should lock domain and
    entity_class with functools.partial.
    """
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
        if device_id in entry.data.get(CONF_DEVICES, []):
            return entry
        else:
            _LOGGER.debug(f"Missing device configuration for device_id {device_id}")
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
        self._reconnect_handle = None
        self._reconnect_delay = _RECONNECT_INITIAL_DELAY
        self._connect_failures = 0
        self._last_host_scan = 0
        self._connect_failure_reason = None
        self._connect_failure_warning_at = 0
        self._connect_failure_suppressed = 0
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

    def async_connect(self, force=False):
        """Connect to device if not already connected."""
        # self.info("async_connect: %d %r %r", self._is_closing, self._connect_task, self._interface)
        if self._dev_config_entry.get(CONF_HOST) == "0.0.0.0":
            self.debug("Skipping connection until a local host is discovered")
            return
        if force:
            self._cancel_reconnect_timer()
        elif self._reconnect_handle is not None:
            self.debug("Skipping connection; reconnect already scheduled")
            return
        if not self._is_closing and self._connect_task is None and not self._interface:
            self._connect_task = asyncio.create_task(self._make_connection())

    async def _make_connection(self):
        """Subscribe localtuya entity events."""
        self.info("Trying to connect to %s...", self._dev_config_entry[CONF_HOST])

        try:
            self._interface = await pytuya.connect(
                self._dev_config_entry[CONF_HOST],
                self._dev_config_entry[CONF_DEVICE_ID],
                self._local_key,
                float(self._dev_config_entry[CONF_PROTOCOL_VERSION]),
                self._dev_config_entry.get(CONF_ENABLE_DEBUG, False),
                self,
            )
            self._interface.add_dps_to_request(self.dps_to_request)
        except Exception as ex:  # pylint: disable=broad-except
            self._log_connect_failure(ex)
            if self._interface is not None:
                await self._interface.close()
                self._interface = None

        if self._interface is not None:
            self._reset_connect_failure_log_state()
            try:
                try:
                    self.debug("Retrieving initial state")
                    status = await self._interface.status()
                    if status is None:
                        raise Exception("Failed to retrieve status")

                    self._interface.start_heartbeat()
                    self.status_updated(status)

                except Exception as ex:
                    if (self._default_reset_dpids is not None) and (
                        len(self._default_reset_dpids) > 0
                    ):
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
                    else:
                        self.error("Initial state update failed, giving up: %r", ex)
                        if self._interface is not None:
                            await self._interface.close()
                            self._interface = None

            except (UnicodeDecodeError, json.decoder.JSONDecodeError) as ex:
                self.warning("Initial state update failed (%s), trying key update", ex)
                await self.update_local_key()

                if self._interface is not None:
                    await self._interface.close()
                    self._interface = None

        if self._interface is not None:
            self._cancel_reconnect_timer()
            self._reconnect_delay = _RECONNECT_INITIAL_DELAY
            self._connect_failures = 0
            # Attempt to restore status for all entities that need to first set
            # the DPS value before the device will respond with status.
            for entity in self._entities:
                await entity.restore_state_when_connected()

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
                and int(self._dev_config_entry[CONF_SCAN_INTERVAL]) > 0
            ):
                self._unsub_interval = async_track_time_interval(
                    self._hass,
                    self._async_refresh,
                    timedelta(seconds=int(self._dev_config_entry[CONF_SCAN_INTERVAL])),
                )

            self.info(f"Successfully connected to {self._dev_config_entry[CONF_HOST]}")

        recovered_host = False
        if self._interface is None:
            self._connect_failures += 1
            recovered_host = await self._async_recover_host_after_failure()

        self._connect_task = None
        if self._interface is None:
            if recovered_host:
                self.async_connect(force=True)
            else:
                self._schedule_reconnect("connection failed")

    def _log_connect_failure(self, ex):
        """Log connection failures without flooding Home Assistant warnings."""
        now = time.monotonic()
        reason = str(ex)
        should_warn = (
            reason != self._connect_failure_reason
            or now - self._connect_failure_warning_at
            >= _CONNECT_FAILURE_WARNING_INTERVAL
        )
        host = self._dev_config_entry[CONF_HOST]

        if should_warn:
            suppressed = self._connect_failure_suppressed
            self._connect_failure_reason = reason
            self._connect_failure_warning_at = now
            self._connect_failure_suppressed = 0

            if suppressed:
                self.warning(
                    "Failed to connect to %s: %s; %d similar failures suppressed",
                    host,
                    ex,
                    suppressed,
                )
            else:
                self.warning("Failed to connect to %s: %s", host, ex)
            return

        self._connect_failure_suppressed += 1
        self.debug("Failed to connect to %s: %s", host, ex)

    def _reset_connect_failure_log_state(self):
        """Reset repeated-failure log throttling after a successful connection."""
        if self._connect_failure_suppressed:
            self.info(
                "Connection to %s recovered; %d similar failures were suppressed",
                self._dev_config_entry[CONF_HOST],
                self._connect_failure_suppressed,
            )
        self._connect_failure_reason = None
        self._connect_failure_warning_at = 0
        self._connect_failure_suppressed = 0

    def update_config(self, dev_config_entry):
        """Apply runtime-safe config updates without requiring a config reload."""
        old_host = self._dev_config_entry.get(CONF_HOST)
        old_local_key = self._local_key
        self._dev_config_entry = dev_config_entry.copy()
        self._local_key = self._dev_config_entry[CONF_LOCAL_KEY]

        host_changed = old_host != self._dev_config_entry.get(CONF_HOST)
        key_changed = old_local_key != self._local_key

        if host_changed:
            self.info(
                "Updated runtime host from %s to %s",
                old_host,
                self._dev_config_entry.get(CONF_HOST),
            )
        if key_changed:
            self.info("Updated runtime local key")

        if host_changed or key_changed:
            self._cancel_reconnect_timer()
        if host_changed:
            self._connect_failures = 0

        return host_changed or key_changed

    async def _async_recover_host_after_failure(self):
        """Try to recover a stale host using device-id MAC evidence."""
        now = time.monotonic()
        include_scan = (
            self._connect_failures >= _HOST_RECOVERY_SCAN_FAILURES
            and now - self._last_host_scan >= _HOST_RECOVERY_SCAN_INTERVAL
        )
        if include_scan:
            self._last_host_scan = now

        dev_id = self._dev_config_entry[CONF_DEVICE_ID]
        current_host = self._dev_config_entry.get(CONF_HOST)
        resolution = await self._hass.async_add_executor_job(
            find_host_for_device_id,
            dev_id,
            current_host,
            include_scan,
        )
        if resolution is None and include_scan:
            resolution = await self._async_probe_lan_for_device_host(current_host)

        if resolution is None or resolution.host == current_host:
            return False

        self.info(
            "Recovered host %s for %s from %s via %s",
            resolution.host,
            resolution.mac,
            current_host,
            resolution.source,
        )
        self._update_host_config(resolution.host)
        return True

    async def _async_probe_lan_for_device_host(self, current_host):
        """Find this device by probing Tuya LAN listeners with its credentials."""
        candidate_hosts = await self._hass.async_add_executor_job(
            scan_subnet_for_tuya_hosts,
            current_host,
        )
        if not candidate_hosts:
            return None

        self.debug(
            "Probing %d Tuya LAN hosts for stale host recovery",
            len(candidate_hosts),
        )

        semaphore = asyncio.Semaphore(_HOST_RECOVERY_PROBE_CONCURRENCY)

        async def _probe(host):
            async with semaphore:
                if await self._async_probe_host_for_device(host):
                    return host
            return None

        tasks = [asyncio.create_task(_probe(host)) for host in candidate_hosts]
        try:
            for task in asyncio.as_completed(tasks):
                host = await task
                if host:
                    for pending in tasks:
                        if pending is not task:
                            pending.cancel()
                    return HostResolution(
                        host,
                        mac_from_device_id(self._dev_config_entry[CONF_DEVICE_ID])
                        or "",
                        "local-key probe",
                    )
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        return None

    async def _async_probe_host_for_device(self, host):
        """Return whether a Tuya LAN host matches this device's credentials."""
        interface = None
        try:
            interface = await pytuya.connect(
                host,
                self._dev_config_entry[CONF_DEVICE_ID],
                self._local_key,
                float(self._dev_config_entry[CONF_PROTOCOL_VERSION]),
                self._dev_config_entry.get(CONF_ENABLE_DEBUG, False),
                timeout=_HOST_RECOVERY_PROBE_TIMEOUT,
            )
            interface.add_dps_to_request(self.dps_to_request)
            status = await asyncio.wait_for(
                interface.status(),
                timeout=_HOST_RECOVERY_PROBE_TIMEOUT,
            )
            return bool(status)
        except Exception as ex:  # pylint: disable=broad-except
            self.debug("Host probe at %s did not match this device: %s", host, ex)
            return False
        finally:
            if interface is not None:
                with contextlib.suppress(Exception):
                    await interface.close()

    def _update_host_config(self, host):
        """Update the stored and runtime host for this device."""
        dev_id = self._dev_config_entry[CONF_DEVICE_ID]
        new_data = dict(self._config_entry.data)
        devices = dict(new_data[CONF_DEVICES])
        dev_config = dict(devices[dev_id])
        dev_config[CONF_HOST] = host
        devices[dev_id] = dev_config
        new_data[CONF_DEVICES] = devices
        new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

        self.update_config(dev_config)
        self._hass.config_entries.async_update_entry(
            self._config_entry,
            data=new_data,
        )

    async def async_reconnect(self):
        """Force a reconnect without unloading the Home Assistant entities."""
        self._cancel_reconnect_timer()
        if self._interface is not None:
            interface = self._interface
            with contextlib.suppress(Exception):
                await interface.close()
        self.async_connect(force=True)

    def _cancel_reconnect_timer(self):
        """Cancel any scheduled reconnect attempt."""
        if self._reconnect_handle is not None:
            self._reconnect_handle.cancel()
            self._reconnect_handle = None

    def _reconnect_timer_fired(self):
        """Handle a scheduled reconnect attempt."""
        self._reconnect_handle = None
        self.async_connect(force=True)

    def _schedule_reconnect(self, reason):
        """Schedule a reconnect using exponential backoff."""
        if (
            self._is_closing
            or self._interface is not None
            or self._connect_task is not None
            or self._reconnect_handle is not None
        ):
            return

        host = self._dev_config_entry.get(CONF_HOST)
        if host == "0.0.0.0":
            self.debug("Skipping reconnect until a local host is discovered")
            return

        delay = self._reconnect_delay
        self.info(
            "Scheduling reconnect to %s in %s seconds after %s",
            host,
            delay,
            reason,
        )
        self._reconnect_handle = self._hass.loop.call_later(
            delay, self._reconnect_timer_fired
        )
        self._reconnect_delay = min(delay * 2, _RECONNECT_MAX_DELAY)

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
        self._cancel_reconnect_timer()
        if self._connect_task is not None:
            task = self._connect_task
            self._connect_task = None
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self._interface is not None:
            await self._interface.close()
            self._interface = None
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
        if self._disconnect_task is not None:
            self._disconnect_task()
            self._disconnect_task = None
        self.info(
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

    def _dispatch_status(self, status=_STATUS_UNCHANGED):
        signal = f"localtuya_{self._dev_config_entry[CONF_DEVICE_ID]}"
        payload = self._status.copy() if status is _STATUS_UNCHANGED else status
        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send, self._hass, signal, payload
        )

    @callback
    def disconnected(self):
        """Device disconnected."""
        self._dispatch_status(None)
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
        if self._disconnect_task is not None:
            self._disconnect_task()
            self._disconnect_task = None
        self._interface = None

        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            current_task = None
        if self._connect_task is not None and self._connect_task is not current_task:
            self._connect_task.cancel()
            self._connect_task = None
        if self._is_closing:
            return
        self.warning("Disconnected - scheduling reconnect")
        self._schedule_reconnect("disconnect")


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
        self._logged_unknown_dps = set()
        self._logged_unset_config = set()

        # Default value is available to be provided by Platform entities if required
        self._default_value = self._config.get(CONF_DEFAULT_VALUE)

        # Determine whether is a passive entity
        self._is_passive_entity = self._config.get(CONF_PASSIVE_ENTITY) or False

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
            if status is None:
                status = {}
            if self._status != status:
                self._status = status.copy()
                if status:
                    self.status_updated()

                # Update HA
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
        if value is None and not self._status:
            self.debug(
                "Entity %s is waiting for DPS index %s",
                self.entity_id,
                dp_index,
            )
        elif value is None and dp_index not in self._logged_unknown_dps:
            self._logged_unknown_dps.add(dp_index)
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
            if conf_item not in self._logged_unset_config:
                self._logged_unset_config.add(conf_item)
                self.warning(
                    "Entity %s is requesting unset index for option %s",
                    self.entity_id,
                    conf_item,
                )
            return None
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
        if (not self.restore_on_reconnect) and (
            (str(self._dp_id) in self._status) or (not self._is_passive_entity)
        ):
            self.debug(
                "Entity %s (DP %d) - Not restoring as restore on reconnect is "
                + "disabled for this entity and the entity has an initial status "
                + "or it is not a passive entity",
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
            if self._is_passive_entity:
                self.debug("No last restored state - using default")
                restore_state = self.default_value()
            else:
                self.debug("Not a passive entity and no state found - aborting restore")
                return

        self.debug(
            "Entity %s (DP %d) - Restoring state: %s",
            self.name,
            self._dp_id,
            str(restore_state),
        )

        # Manually initialise
        await self._device.set_dp(restore_state, self._dp_id)
