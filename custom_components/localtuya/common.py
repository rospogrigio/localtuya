"""Code shared between all platforms."""
import asyncio
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
    CONF_NO_CLOUD,
    CONF_PASSIVE_ENTITY,
    CONF_PROTOCOL_VERSION,
    CONF_RESET_DPIDS,
    CONF_RESTORE_ON_RECONNECT,
    DATA_CLOUD,
    DOMAIN,
    TUYA_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

# Minimum time between two automatic refreshes of the cloud device list
CLOUD_REFRESH_INTERVAL = timedelta(minutes=5)
DATA_CLOUD_LOCK = "cloud_lock"
DATA_CLOUD_REFRESHED = "cloud_refreshed"


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


async def async_refresh_cloud_devices(hass, entry, force=False):
    """Refresh the list of devices retrieved from the cloud.

    Unless forced, the list is refreshed at most once per CLOUD_REFRESH_INTERVAL,
    so that several devices failing to connect result in a single request.
    """
    domain_data = hass.data[DOMAIN]
    cloud_api = domain_data.get(DATA_CLOUD)
    if cloud_api is None or entry.data.get(CONF_NO_CLOUD, True):
        return

    async with domain_data.setdefault(DATA_CLOUD_LOCK, asyncio.Lock()):
        last_refresh = domain_data.get(DATA_CLOUD_REFRESHED)
        if (
            not force
            and last_refresh is not None
            and time.monotonic() - last_refresh < CLOUD_REFRESH_INTERVAL.total_seconds()
        ):
            return
        domain_data[DATA_CLOUD_REFRESHED] = time.monotonic()

        try:
            res = await cloud_api.async_get_devices_list()
            if res != "ok":
                # The access token may have expired: log in again and retry
                _LOGGER.debug("Cloud API get_devices_list failed (%s), retrying", res)
                res = await cloud_api.async_get_access_token()
                if res == "ok":
                    res = await cloud_api.async_get_devices_list()
        except Exception as ex:  # pylint: disable=broad-except
            res = repr(ex)
        if res != "ok":
            _LOGGER.warning("Failed to refresh cloud device list: %s", res)


async def async_get_new_local_keys(hass, entry, force=False):
    """Return the local_keys retrieved from the cloud that differ from the config.

    Re-pairing a device generates a new local_key. The cloud device list is
    refreshed if forced or if the cached one has no new keys.
    """

    def changed_keys():
        cloud_api = hass.data[DOMAIN].get(DATA_CLOUD)
        cloud_devs = cloud_api.device_list if cloud_api else {}
        return {
            dev_id: cloud_devs[dev_id][CONF_LOCAL_KEY]
            for dev_id, dev in entry.data[CONF_DEVICES].items()
            if cloud_devs.get(dev_id, {}).get(CONF_LOCAL_KEY)
            not in (None, "", dev[CONF_LOCAL_KEY])
        }

    new_keys = {} if force else changed_keys()
    if not new_keys:
        await async_refresh_cloud_devices(hass, entry, force)
        new_keys = changed_keys()
    return new_keys


@callback
def async_save_local_keys(hass, entry, new_keys):
    """Store new local_keys in the config entry, which reloads it."""
    devices = dict(entry.data[CONF_DEVICES])
    for dev_id, local_key in new_keys.items():
        _LOGGER.info("Updating local_key for device %s from cloud", dev_id)
        devices[dev_id] = {**devices[dev_id], CONF_LOCAL_KEY: local_key}

    new_data = {**entry.data, CONF_DEVICES: devices}
    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
    hass.config_entries.async_update_entry(entry, data=new_data)


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
        # self.info("async_connect: %d %r %r", self._is_closing, self._connect_task, self._interface)
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
            self.warning(
                f"Failed to connect to {self._dev_config_entry[CONF_HOST]}: %s", ex
            )
            if self._interface is not None:
                await self._interface.close()
                self._interface = None

        if self._interface is not None:
            status = None
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

            except Exception as ex:  # pylint: disable=broad-except
                self.error("Initial state update failed, giving up: %r", ex)
                if self._interface is not None:
                    await self._interface.close()
                    self._interface = None

            if not status:
                # A re-paired device gets a new local_key: it still accepts
                # connections, but no (decryptable) status is received.
                new_keys = await async_get_new_local_keys(
                    self._hass, self._config_entry
                )
                if new_keys:
                    # Saving reloads the config entry: close the connection first
                    if self._interface is not None:
                        await self._interface.close()
                        self._interface = None
                    async_save_local_keys(self._hass, self._config_entry, new_keys)

        if self._interface is not None:
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

        self._connect_task = None

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

        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None
        self.warning("Disconnected - waiting for discovery broadcast")


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
