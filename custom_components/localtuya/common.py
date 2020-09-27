"""Code shared between all platforms."""
import logging
from time import time, sleep
from threading import Lock

from homeassistant.helpers.entity import Entity

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_ID,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_PLATFORM,
    CONF_ENTITIES,
)

from . import pytuya
from .const import CONF_LOCAL_KEY, CONF_PROTOCOL_VERSION, DOMAIN, TUYA_DEVICE

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

    tuyainterface = hass.data[DOMAIN][config_entry.entry_id][TUYA_DEVICE]

    return tuyainterface, entities_to_setup


def get_entity_config(config_entry, dps_id):
    """Return entity config for a given DPS id."""
    for entity in config_entry.data[CONF_ENTITIES]:
        if entity[CONF_ID] == dps_id:
            return entity
    raise Exception(f"missing entity config for id {dps_id}")


class TuyaDevice:
    """Cache wrapper for pytuya.TuyaInterface."""

    def __init__(self, config_entry):
        """Initialize the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        self._interface = pytuya.TuyaInterface(
            config_entry[CONF_DEVICE_ID],
            config_entry[CONF_HOST],
            config_entry[CONF_LOCAL_KEY],
            float(config_entry[CONF_PROTOCOL_VERSION]),
        )
        for entity in config_entry[CONF_ENTITIES]:
            # this has to be done in case the device type is type_0d
            self._interface.add_dps_to_request(entity[CONF_ID])
        self._friendly_name = config_entry[CONF_FRIENDLY_NAME]
        self._lock = Lock()

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return self._interface.id

    def __get_status(self):
        _LOGGER.debug("running def __get_status from TuyaDevice")
        for i in range(5):
            try:
                status = self._interface.status()
                return status
            except Exception:
                print(
                    "Failed to update status of device [{}]".format(
                        self._interface.address
                    )
                )
                sleep(1.0)
                if i + 1 == 3:
                    _LOGGER.error(
                        "Failed to update status of device %s", self._interface.address
                    )
                    #                    return None
                    raise ConnectionError("Failed to update status .")

    def set_dps(self, state, dps_index):
        # _LOGGER.info("running def set_dps from cover")
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        for i in range(5):
            try:
                return self._interface.set_dps(state, dps_index)
            except Exception:
                print(
                    "Failed to set status of device [{}]".format(
                        self._interface.address
                    )
                )
                if i + 1 == 3:
                    _LOGGER.error(
                        "Failed to set status of device %s", self._interface.address
                    )
                    return

    #                    raise ConnectionError("Failed to set status.")

    def status(self):
        """Get state of Tuya switch and cache the results."""
        _LOGGER.debug("running def status(self) from TuyaDevice")
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 15:
                sleep(0.5)
                self._cached_status = self.__get_status()
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()


class LocalTuyaEntity(Entity):
    """Representation of a Tuya entity."""

    def __init__(self, device, config_entry, dps_id, **kwargs):
        """Initialize the Tuya entity."""
        self._device = device
        self._config_entry = config_entry
        self._config = get_entity_config(config_entry, dps_id)
        self._available = False
        self._dps_id = dps_id
        self._status = None

    @property
    def device_info(self):
        """Return device information for the device registry."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"local_{self._device.unique_id}")
            },
            "name": self._config_entry.data[CONF_FRIENDLY_NAME],
            "manufacturer": "Unknown",
            "model": "Tuya generic",
            "sw_version": self._config_entry.data[CONF_PROTOCOL_VERSION],
        }

    @property
    def name(self):
        """Get name of Tuya entity."""
        return self._config[CONF_FRIENDLY_NAME]

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"local_{self._device.unique_id}_{self._dps_id}"

    @property
    def available(self):
        """Return if device is available or not."""
        return self._available

    def dps(self, dps_index):
        """Return cached value for DPS index."""
        value = self._status["dps"].get(str(dps_index))
        if value is None:
            _LOGGER.warning(
                "Entity %s is requesting unknown DPS index %s",
                self.entity_id,
                dps_index,
            )
        return value

    def update(self):
        """Update state of Tuya entity."""
        try:
            self._status = self._device.status()
            self.status_updated()
        except Exception:
            self._available = False
        else:
            self._available = True

    def status_updated(self):
        """Device status was updated.

        Override in subclasses and update entity specific state.
        """
