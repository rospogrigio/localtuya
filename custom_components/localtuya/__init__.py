"""The LocalTuya integration integration."""
import asyncio
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

from .const import CONF_LOCAL_KEY, CONF_PROTOCOL_VERSION, DOMAIN


import pprint

pp = pprint.PrettyPrinter(indent=4)

_LOGGER = logging.getLogger(__name__)

DEFAULT_ID = "1"
DEFAULT_PROTOCOL_VERSION = 3.3

UNSUB_LISTENER = "unsub_listener"

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
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    unsub_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        UNSUB_LISTENER: unsub_listener,
    }

    for platform in set(entity[CONF_PLATFORM] for entity in entry.data[CONF_ENTITIES]):
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in set(
                    entity[CONF_PLATFORM] for entity in entry.data[CONF_ENTITIES]
                )
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id][UNSUB_LISTENER]()
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)
