"""The LocalTuya integration integration."""
import logging
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_ID,
    CONF_ICON,
    CONF_NAME,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_PLATFORM,
    CONF_ENTITIES,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

from . import pytuya
from .const import CONF_LOCAL_KEY, CONF_PROTOCOL_VERSION, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_ID = "1"
DEFAULT_PROTOCOL_VERSION = 3.3

BASE_PLATFORM_SCHEMA = {
    vol.Optional(CONF_ICON): cv.icon,  # Deprecated: not used
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Optional(CONF_NAME): cv.string,  # Deprecated: not used
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION): vol.Coerce(
        float
    ),
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
}


def prepare_setup_entities(config_entry, platform):
    """Prepare ro setup entities for a platform."""
    entities_to_setup = [
        entity
        for entity in config_entry.data[CONF_ENTITIES]
        if entity[CONF_PLATFORM] == platform
    ]
    if not entities_to_setup:
        return None, None

    device = pytuya.TuyaDevice(
        config_entry.data[CONF_DEVICE_ID],
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_LOCAL_KEY],
    )
    device.set_version(float(config_entry.data[CONF_PROTOCOL_VERSION]))

    for device_config in entities_to_setup:
        # this has to be done in case the device type is type_0d
        device.add_dps_to_request(device_config[CONF_ID])

    return device, entities_to_setup


def import_from_yaml(hass, config, platform):
    """Import configuration from YAML."""
    config[CONF_PLATFORM] = platform
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config
        )
    )

    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    for platform in set(entity[CONF_PLATFORM] for entity in entry.data[CONF_ENTITIES]):
        #        print("ASE*** [{}] [{}]".format(entry.data["entities"][0][CONF_PLATFORM], platform))
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Nothing is stored and no persistent connections exist, so nothing to do
    return True


def get_entity_config(config_entry, dps_id):
    """Return entity config for a given DPS id."""
    for entity in config_entry.data[CONF_ENTITIES]:
        if entity[CONF_ID] == dps_id:
            return entity
    raise Exception(f"missing entity config for id {dps_id}")


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
        value = self._status["dps"].get(dps_index)
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
