"""Config flow for LocalTuya integration integration."""
import logging
from importlib import import_module

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_ID,
    CONF_HOST,
    CONF_DEVICE_ID,
    CONF_FRIENDLY_NAME,
    CONF_PLATFORM,
)
import homeassistant.helpers.config_validation as cv

from . import pytuya
from .const import (  # pylint: disable=unused-import
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    CONF_DPS_STRINGS,
    DOMAIN,
    PLATFORMS,
)
from .discovery import discover

_LOGGER = logging.getLogger(__name__)

DISCOVER_TIMEOUT = 6.0

PLATFORM_TO_ADD = "platform_to_add"
NO_ADDITIONAL_PLATFORMS = "no_additional_platforms"
DISCOVERED_DEVICE = "discovered_device"

CUSTOM_DEVICE = "..."

BASIC_INFO_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FRIENDLY_NAME): str,
        vol.Required(CONF_LOCAL_KEY): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(["3.1", "3.3"]),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FRIENDLY_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_LOCAL_KEY): str,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(["3.1", "3.3"]),
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Required(CONF_FRIENDLY_NAME): cv.string,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(["3.1", "3.3"]),
    }
)

PICK_ENTITY_SCHEMA = vol.Schema(
    {vol.Required(PLATFORM_TO_ADD, default=PLATFORMS[0]): vol.In(PLATFORMS)}
)


def user_schema(devices):
    """Create schema for user step."""
    devices = [f"{ip} ({dev['gwId']})" for ip, dev in devices.items()]
    return vol.Schema(
        {vol.Required(DISCOVERED_DEVICE): vol.In(devices + [CUSTOM_DEVICE])}
    )


def schema_defaults(schema, dps_list=None, **defaults):
    """Create a new schema with default values filled in."""
    copy = schema.extend({})
    for field, field_type in copy.schema.items():
        if isinstance(field_type, vol.In):
            value = None
            for dps in dps_list or []:
                if dps.startswith(f"{defaults.get(field)} "):
                    value = dps
                    break

            if value in field_type.container:
                field.default = vol.default_factory(value)
                continue

        if field.schema in defaults:
            field.default = vol.default_factory(defaults[field])
    return copy


def dps_string_list(dps_data):
    """Return list of friendly DPS values."""
    return [f"{id} (value: {value})" for id, value in dps_data.items()]


def gen_dps_strings():
    """Generate list of DPS values."""
    return [f"{dp} (value: ?)" for dp in range(1, 256)]


def platform_schema(platform, dps_strings, allow_id=True, yaml=False):
    """Generate input validation schema for a platform."""
    schema = {}
    if yaml:
        # In YAML mode we force the specified platform to match flow schema
        schema[vol.Required(CONF_PLATFORM)] = vol.In([platform])
    if allow_id:
        schema[vol.Required(CONF_ID)] = vol.In(dps_strings)
    schema[vol.Required(CONF_FRIENDLY_NAME)] = str
    return vol.Schema(schema).extend(flow_schema(platform, dps_strings))


def flow_schema(platform, dps_strings):
    """Return flow schema for a specific platform."""
    integration_module = ".".join(__name__.split(".")[:-1])
    return import_module("." + platform, integration_module).flow_schema(dps_strings)


def strip_dps_values(user_input, dps_strings):
    """Remove values and keep only index for DPS config items."""
    stripped = {}
    for field, value in user_input.items():
        if value in dps_strings:
            stripped[field] = int(user_input[field].split(" ")[0])
        else:
            stripped[field] = user_input[field]
    return stripped


def config_schema():
    """Build schema used for setting up component."""
    entity_schemas = [
        platform_schema(platform, range(1, 256), yaml=True) for platform in PLATFORMS
    ]
    return vol.Schema(
        {
            DOMAIN: vol.All(
                cv.ensure_list,
                [
                    DEVICE_SCHEMA.extend(
                        {vol.Required(CONF_ENTITIES): [vol.Any(*entity_schemas)]}
                    )
                ],
            )
        },
        extra=vol.ALLOW_EXTRA,
    )


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""
    detected_dps = {}

    interface = None
    try:
        interface = await pytuya.connect(
            data[CONF_HOST],
            data[CONF_DEVICE_ID],
            data[CONF_LOCAL_KEY],
            float(data[CONF_PROTOCOL_VERSION]),
        )

        detected_dps = await interface.detect_available_dps()
    except (ConnectionRefusedError, ConnectionResetError):
        raise CannotConnect
    except ValueError:
        raise InvalidAuth
    finally:
        if interface:
            interface.close()

    return dps_string_list(detected_dps)


class LocaltuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LocalTuya integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return LocalTuyaOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize a new LocaltuyaConfigFlow."""
        self.basic_info = None
        self.dps_strings = []
        self.platform = None
        self.devices = {}
        self.selected_device = None
        self.entities = []

    async def async_step_user(self, user_input=None):
        """Handle initial step."""
        errors = {}
        if user_input is not None:
            if user_input[DISCOVERED_DEVICE] != CUSTOM_DEVICE:
                self.selected_device = user_input[DISCOVERED_DEVICE].split(" ")[0]
            return await self.async_step_basic_info()

        try:
            devices = await discover(DISCOVER_TIMEOUT, self.hass.loop)
            self.devices = {
                ip: dev
                for ip, dev in devices.items()
                if dev["gwId"] not in self._async_current_ids()
            }
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("discovery failed")
            errors["base"] = "discovery_failed"

        return self.async_show_form(
            step_id="user", errors=errors, data_schema=user_schema(self.devices)
        )

    async def async_step_basic_info(self, user_input=None):
        """Handle input of basic info."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                self.basic_info = user_input
                self.dps_strings = await validate_input(self.hass, user_input)
                return await self.async_step_pick_entity_type()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        defaults = {}
        defaults.update(user_input or {})
        if self.selected_device is not None:
            device = self.devices[self.selected_device]
            defaults[CONF_HOST] = device.get("ip")
            defaults[CONF_DEVICE_ID] = device.get("gwId")
            defaults[CONF_PROTOCOL_VERSION] = device.get("version")

        return self.async_show_form(
            step_id="basic_info",
            data_schema=schema_defaults(BASIC_INFO_SCHEMA, **defaults),
            errors=errors,
        )

    async def async_step_pick_entity_type(self, user_input=None):
        """Handle asking if user wants to add another entity."""
        if user_input is not None:
            if user_input.get(NO_ADDITIONAL_PLATFORMS):
                config = {
                    **self.basic_info,
                    CONF_DPS_STRINGS: self.dps_strings,
                    CONF_ENTITIES: self.entities,
                }
                return self.async_create_entry(
                    title=config[CONF_FRIENDLY_NAME], data=config
                )

            self.platform = user_input[PLATFORM_TO_ADD]
            return await self.async_step_add_entity()

        # Add a checkbox that allows bailing out from config flow iff at least one
        # entity has been added
        schema = PICK_ENTITY_SCHEMA
        if self.platform is not None:
            schema = schema.extend(
                {vol.Required(NO_ADDITIONAL_PLATFORMS, default=True): bool}
            )

        return self.async_show_form(step_id="pick_entity_type", data_schema=schema)

    async def async_step_add_entity(self, user_input=None):
        """Handle adding a new entity."""
        errors = {}
        if user_input is not None:
            already_configured = any(
                switch[CONF_ID] == user_input[CONF_ID] for switch in self.entities
            )
            if not already_configured:
                user_input[CONF_PLATFORM] = self.platform
                self.entities.append(strip_dps_values(user_input, self.dps_strings))
                return await self.async_step_pick_entity_type()

            errors["base"] = "entity_already_configured"

        return self.async_show_form(
            step_id="add_entity",
            data_schema=platform_schema(self.platform, self.dps_strings),
            errors=errors,
            description_placeholders={"platform": self.platform},
        )

    async def async_step_import(self, user_input):
        """Handle import from YAML."""
        await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
        self._abort_if_unique_id_configured(updates=user_input)
        return self.async_create_entry(
            title=f"{user_input[CONF_FRIENDLY_NAME]} (YAML)", data=user_input
        )


class LocalTuyaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for LocalTuya integration."""

    def __init__(self, config_entry):
        """Initialize localtuya options flow."""
        self.config_entry = config_entry
        self.dps_strings = config_entry.data.get(CONF_DPS_STRINGS, gen_dps_strings())
        self.entities = config_entry.data[CONF_ENTITIES]
        self.data = None

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        device_id = self.config_entry.data[CONF_DEVICE_ID]
        if user_input is not None:
            self.data = {
                CONF_DEVICE_ID: device_id,
                CONF_DPS_STRINGS: self.dps_strings,
                CONF_ENTITIES: [],
            }
            self.data.update(user_input)
            return await self.async_step_entity()

        # Not supported for YAML imports
        if self.config_entry.source == config_entries.SOURCE_IMPORT:
            return await self.async_step_yaml_import()

        return self.async_show_form(
            step_id="init",
            data_schema=schema_defaults(OPTIONS_SCHEMA, **self.config_entry.data),
            description_placeholders={"device_id": device_id},
        )

    async def async_step_entity(self, user_input=None):
        """Manage entity settings."""
        errors = {}
        if user_input is not None:
            entity = strip_dps_values(user_input, self.dps_strings)
            entity[CONF_ID] = self.current_entity[CONF_ID]
            entity[CONF_PLATFORM] = self.current_entity[CONF_PLATFORM]
            self.data[CONF_ENTITIES].append(entity)

            if len(self.entities) == len(self.data[CONF_ENTITIES]):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=self.data[CONF_FRIENDLY_NAME],
                    data=self.data,
                )
                return self.async_create_entry(title="", data={})

        schema = platform_schema(
            self.current_entity[CONF_PLATFORM], self.dps_strings, allow_id=False
        )
        return self.async_show_form(
            step_id="entity",
            errors=errors,
            data_schema=schema_defaults(
                schema, self.dps_strings, **self.current_entity
            ),
            description_placeholders={
                "id": self.current_entity[CONF_ID],
                "platform": self.current_entity[CONF_PLATFORM],
            },
        )

    async def async_step_yaml_import(self, user_input=None):
        """Manage YAML imports."""
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="yaml_import")

    @property
    def current_entity(self):
        """Existing configuration for entity currently being edited."""
        return self.entities[len(self.data[CONF_ENTITIES])]


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
