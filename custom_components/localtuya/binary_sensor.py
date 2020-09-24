"""
Platform to prsent any Tuya DP as a binary sensor.

Sample config yaml

sensor:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    friendly_name: Current
    protocol_version: 3.3
    id: 18
    state_on: "true" (optional, default is "true")
    state_off: "false" (optional, default is "false")
    device_class: current
"""
import logging
from time import time, sleep
from threading import Lock

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DOMAIN,
    DEVICE_CLASSES_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import (
    CONF_ID,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
)

from .common import LocalTuyaEntity, prepare_setup_entities

_LOGGER = logging.getLogger(__name__)

CONF_STATE_ON = "state_on"
CONF_STATE_OFF = "state_off"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_STATE_ON, default="True"): str,
        vol.Required(CONF_STATE_OFF, default="False"): str,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up a Tuya sensor based on a config entry."""
    device, entities_to_setup = prepare_setup_entities(config_entry, DOMAIN)
    if not entities_to_setup:
        return

    sensors = []
    for device_config in entities_to_setup:
        sensors.append(
            LocaltuyaBinarySensor(
                TuyaCache(device, config_entry.data[CONF_FRIENDLY_NAME]),
                config_entry,
                device_config[CONF_ID],
            )
        )

    async_add_entities(sensors, True)


class TuyaCache:
    """Cache wrapper for pytuya.TuyaDevice."""

    def __init__(self, device, friendly_name):
        """Initialize the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        self._device = device
        self._friendly_name = friendly_name
        self._lock = Lock()

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return self._device.id

    def __get_status(self):
        for i in range(5):
            try:
                status = self._device.status()
                return status
            except Exception:
                print(
                    "Failed to update status of device [{}]".format(
                        self._device.address
                    )
                )
                sleep(1.0)
                if i + 1 == 3:
                    _LOGGER.error(
                        "Failed to update status of device %s", self._device.address
                    )
                    #                    return None
                    raise ConnectionError("Failed to update status .")

    def set_dps(self, state, dps_index):
        """Change the Tuya sensor status and clear the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        for i in range(5):
            try:
                return self._device.set_dps(state, dps_index)
            except Exception:
                print(
                    "Failed to set status of device [{}]".format(self._device.address)
                )
                if i + 1 == 3:
                    _LOGGER.error(
                        "Failed to set status of device %s", self._device.address
                    )
                    return

        #                    raise ConnectionError("Failed to set status.")

    def status(self):
        """Get state of Tuya sensor and cache the results."""
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


class LocaltuyaBinarySensor(LocalTuyaEntity, BinarySensorEntity):
    """Representation of a Tuya binary sensor."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya binary sensor."""
        super().__init__(device, config_entry, sensorid, **kwargs)
        self._is_on = False

    @property
    def is_on(self):
        """Return sensor state."""
        return self._is_on

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    def status_updated(self):
        """Device status was updated."""
        state = str(self.dps(self._dps_id)).lower()
        if state == self._config[CONF_STATE_ON].lower():
            self._is_on = True
        elif state == self._config[CONF_STATE_OFF].lower():
            self._is_on = False
        else:
            _LOGGER.warning(
                "State for entity %s did not match state patterns", self.entity_id
            )
