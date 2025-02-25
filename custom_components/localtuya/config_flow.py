"""Config flow for LocalTuya integration integration."""

import asyncio
import errno
import logging
import time
from importlib import import_module
from functools import partial
from collections.abc import Coroutine
from typing import Any
from copy import deepcopy


import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)
import voluptuous as vol
from homeassistant import exceptions
from homeassistant.core import callback, HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_ENTITY_CATEGORY,
    CONF_HOST,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EntityCategory,
)

from .coordinator import HassLocalTuyaData
from .core import pytuya
from .core.cloud_api import TUYA_ENDPOINTS, TuyaCloudApi
from .core.helpers import templates, get_gateway_by_deviceid, gen_localtuya_entities
from .const import (
    ATTR_UPDATED_AT,
    CONF_ADD_DEVICE,
    CONF_CONFIGURE_CLOUD,
    CONF_DPS_STRINGS,
    CONF_EDIT_DEVICE,
    CONF_ENABLE_ADD_ENTITIES,
    CONF_ENABLE_DEBUG,
    CONF_GATEWAY_ID,
    CONF_LOCAL_KEY,
    CONF_MANUAL_DPS,
    CONF_MODEL,
    CONF_NODE_ID,
    CONF_NO_CLOUD,
    CONF_PRODUCT_KEY,
    CONF_PRODUCT_NAME,
    CONF_PROTOCOL_VERSION,
    CONF_RESET_DPIDS,
    CONF_TUYA_GWID,
    CONF_TUYA_IP,
    CONF_TUYA_VERSION,
    CONF_USER_ID,
    DATA_DISCOVERY,
    DEFAULT_CATEGORIES,
    DOMAIN,
    ENTITY_CATEGORY,
    PLATFORMS,
    SUPPORTED_PROTOCOL_VERSIONS,
    CONF_DEVICE_SLEEP_TIME,
)
from .discovery import discover

_LOGGER = logging.getLogger(__name__)

ENTRIES_VERSION = 4

PLATFORM_TO_ADD = "platform_to_add"
USE_TEMPLATE = "use_template"
TEMPLATES = "templates"
NO_ADDITIONAL_ENTITIES = "no_additional_entities"
SELECTED_DEVICE = "selected_device"
EXPORT_CONFIG = "export_config"

TUYA_CATEGORY = "category"
DEVICE_CLOUD_DATA = "device_cloud_data"

# Using list method so we can translate options.
CONFIGURE_MENU = [CONF_ADD_DEVICE, CONF_EDIT_DEVICE, CONF_CONFIGURE_CLOUD]


def col_to_select(
    opt_list: dict | list, multi_select=False, is_dps=False, custom_value=False
) -> SelectSelector:
    """Convert collections to SelectSelectorConfig."""
    if type(opt_list) == dict:
        return SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=str(v), label=k) for k, v in opt_list.items()
                ],
                mode=SelectSelectorMode.DROPDOWN,
                custom_value=custom_value,
                multiple=True if multi_select else False,
            )
        )
    elif type(opt_list) == list:
        # value used the same method as func available_dps_string, no spaces values.
        return SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(
                        value=str(kv).split(" ")[0] if is_dps else str(kv),
                        label=str(kv),
                    )
                    for kv in opt_list
                ],
                mode=SelectSelectorMode.DROPDOWN,
                custom_value=custom_value,
                multiple=True if multi_select else False,
            )
        )


CLOUD_CONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION, default="eu"): col_to_select(TUYA_ENDPOINTS),
        vol.Optional(CONF_CLIENT_ID): cv.string,
        vol.Optional(CONF_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_USER_ID): cv.string,
        vol.Optional(CONF_USERNAME, default=DOMAIN): cv.string,
        vol.Required(CONF_NO_CLOUD, default=False): bool,
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FRIENDLY_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Required(CONF_PROTOCOL_VERSION, default="auto"): col_to_select(
            ["auto"] + sorted(SUPPORTED_PROTOCOL_VERSIONS)
        ),
        vol.Required(CONF_ENABLE_DEBUG, default=False): bool,
        vol.Optional(CONF_SCAN_INTERVAL): int,
        vol.Optional(CONF_MANUAL_DPS): cv.string,
        vol.Optional(CONF_RESET_DPIDS): str,
        vol.Optional(CONF_DEVICE_SLEEP_TIME): int,
        vol.Optional(CONF_NODE_ID, default=None): vol.Any(None, cv.string),
    }
)

PICK_ENTITY_SCHEMA = vol.Schema(
    {vol.Required(PLATFORM_TO_ADD, default="switch"): col_to_select(PLATFORMS)}
)


CONF_MASS_CONFIGURE = "mass_configure"
MASS_CONFIGURE_SCHEMA = {vol.Optional(CONF_MASS_CONFIGURE, default=False): bool}
CUSTOM_DEVICE = {"Add Device Manually": "..."}


class LocaltuyaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LocalTuya integration."""

    VERSION = ENTRIES_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return LocalTuyaOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize a new LocaltuyaConfigFlow."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        placeholders = {}
        if user_input is not None:
            if user_input.get(CONF_NO_CLOUD):
                for i in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
                    user_input[i] = ""
                return await self._create_entry(user_input)

            cloud_api, res = await attempt_cloud_connection(user_input)

            if not res:
                return await self._create_entry(user_input)
            errors["base"] = res["reason"]
            # 1004 = Secret, 1106 = USER ID, 2009 = Client ID
            if "1106" in res["msg"]:
                res["msg"] = f"{res['msg']} Check UserID or country code!"
            if "1004" in res["msg"]:
                res["msg"] = f"{res['msg']} Check Secret Key!"
            placeholders = {"msg": res["msg"]}

        defaults = {}
        defaults.update(user_input or {})

        return self.async_show_form(
            step_id="user",
            data_schema=schema_defaults(CLOUD_CONFIGURE_SCHEMA, **defaults),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _create_entry(self, user_input):
        """Register new entry."""
        # if self._async_current_entries():
        #     return self.async_abort(reason="already_configured")

        await self.async_set_unique_id(user_input.get(CONF_USER_ID))
        self._abort_if_unique_id_configured()

        user_input[CONF_DEVICES] = {}

        return self.async_create_entry(
            title=user_input.get(CONF_USERNAME),
            data=user_input,
        )

    async def async_step_import(self, user_input):
        """Handle import from YAML."""
        _LOGGER.error(
            "Configuration via YAML file is no longer supported by this integration."
        )


class LocalTuyaOptionsFlowHandler(OptionsFlow):
    """Handle options flow for LocalTuya integration."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize localtuya options flow."""
        self._entry_id = config_entry.entry_id

        self.selected_device = None
        self.nodeID = None

        self.editing_device: bool = False
        self.device_data: dict = None
        self.dps_strings = []
        self.selected_platform = None
        self.discovered_devices = {}
        self.entities = []
        self.use_template = False
        self.template_device = None

    @property
    def localtuya_data(self) -> HassLocalTuyaData:
        return self.hass.data[DOMAIN][self._entry_id]

    @property
    def cloud_data(self) -> TuyaCloudApi:
        return self.localtuya_data.cloud_data

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        configure_menu = CONFIGURE_MENU.copy()
        # Remove Reconfigure existing device option if there is no existed devices.
        if not self.config_entry.data[CONF_DEVICES]:
            configure_menu.pop(configure_menu.index(CONF_EDIT_DEVICE))

        if not self.config_entry.data.get(CONF_NO_CLOUD, True):
            self.hass.async_create_task(self.cloud_data.async_get_devices_list())

        return self.async_show_menu(step_id="init", menu_options=configure_menu)

    async def async_step_configure_cloud(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        placeholders = {}
        if user_input is not None:
            username = user_input.get(CONF_USERNAME)
            if user_input.get(CONF_NO_CLOUD):
                new_data = self.config_entry.data.copy()
                new_data.update(user_input)
                for i in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
                    new_data[i] = ""

                return self._update_entry(new_data, new_title=username)

            cloud_api, res = await attempt_cloud_connection(user_input)

            if not res:
                new_data = self.config_entry.data.copy()
                new_data.update(user_input)
                cloud_devs = cloud_api.device_list
                for dev_id, dev in new_data[CONF_DEVICES].items():
                    if CONF_MODEL not in dev and dev_id in cloud_devs:
                        model = cloud_devs[dev_id].get(CONF_PRODUCT_NAME)
                        new_data[CONF_DEVICES][dev_id][CONF_MODEL] = model

                return self._update_entry(new_data, new_title=username)

            errors["base"] = res["reason"]
            placeholders = {"msg": res["msg"]}

        defaults = self.config_entry.data.copy()
        defaults.update(user_input or {})
        defaults[CONF_NO_CLOUD] = False

        return self.async_show_form(
            step_id="configure_cloud",
            data_schema=schema_defaults(CLOUD_CONFIGURE_SCHEMA, **defaults),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_add_device(self, user_input=None):
        """Handle adding a new device."""
        # Use cache if available or fallback to manual discovery
        self.editing_device = False
        self.selected_device = None
        errors = {}
        if user_input is not None:
            if user_input[SELECTED_DEVICE] != CUSTOM_DEVICE["Add Device Manually"]:
                self.selected_device = user_input[SELECTED_DEVICE]

            if user_input.pop(CONF_MASS_CONFIGURE, False):
                # Handle auto configure all recognized devices.
                await self.cloud_data.async_get_devices_dps_query()
                devices, fails = await setup_localtuya_devices(
                    self.hass,
                    self.config_entry.entry_id,
                    self.discovered_devices,
                    self.cloud_data.device_list,
                    log_fails=True,
                )
                if devices:
                    devices_sucessed, devices_fails = "", ""
                    for sucess_dev in devices.values():
                        devices_sucessed += f"\n{sucess_dev[CONF_FRIENDLY_NAME]}"
                    for fail_dev in fails.values():
                        devices_fails += f"\n{fail_dev['name']}: {fail_dev['reason']}"

                    msg = f"Succeeded devices: ``{len(devices)}``\n ```{devices_sucessed}\n```"
                    if fails:
                        msg += f" \n Failed devices: ``{len(fails)}``\n ```{devices_fails}\n```"

                    return await self.async_step_confirm(
                        msg=msg,
                        confirm_callback=self._update_entry,
                        callback_args=(devices, CONF_DEVICES),
                    )

            return await self.async_step_configure_device()

        self.discovered_devices = {}
        data = self.hass.data.get(DOMAIN)

        if data and DATA_DISCOVERY in data:
            self.discovered_devices = data[DATA_DISCOVERY].devices
        else:
            self.discovered_devices, errors = await discover_devices()

        allDevices = mergeDevicesList(
            self.discovered_devices, self.cloud_data.device_list
        )

        self.discovered_devices = allDevices
        devices = {}
        # To avoid duplicated entities we will get all devices in every hub.
        entries = self.hass.config_entries.async_entries(DOMAIN)
        configured_Devices = []
        for entry in entries:
            for devID in entry.data[CONF_DEVICES].keys():
                configured_Devices.append(devID)

        for dev_id, dev in allDevices.items():
            if dev_id not in configured_Devices:
                if dev.get(CONF_NODE_ID, None) is not None:
                    devices[dev_id] = "Sub Device"
                else:
                    devices[dev_id] = dev.get(CONF_TUYA_IP, "")

        return self.async_show_form(
            step_id="add_device",
            data_schema=devices_schema(devices, self.cloud_data.device_list),
            errors=errors,
        )

    async def async_step_edit_device(self, user_input=None):
        """Handle editing a device."""
        self.editing_device = True
        # Use cache if available or fallback to manual discovery
        errors = {}
        if user_input is not None:
            self.selected_device = user_input[SELECTED_DEVICE]
            dev_conf = self.config_entry.data[CONF_DEVICES][self.selected_device]
            self.dps_strings = dev_conf.get(CONF_DPS_STRINGS, gen_dps_strings())
            self.entities = dev_conf[CONF_ENTITIES]
            return await self.async_step_configure_device()

        devices = {}
        for dev_id, configured_dev in self.config_entry.data[CONF_DEVICES].items():
            if configured_dev.get(CONF_NODE_ID, None):
                devices[dev_id] = "Sub Device"
            else:
                devices[dev_id] = configured_dev[CONF_HOST]

        return self.async_show_form(
            step_id="edit_device",
            data_schema=devices_schema(
                devices,
                self.cloud_data.device_list,
                False,
                self.config_entry.data[CONF_DEVICES],
            ),
            errors=errors,
        )

    async def async_step_device_setup_method(self, user_input=None):
        """Manage basic options."""
        DEVICE_SETUP_METHOD = [
            "auto_configure_device",
            "pick_entity_type",
            "choose_template",
        ]
        return self.async_show_menu(
            step_id="device_setup_method",
            menu_options=DEVICE_SETUP_METHOD,
        )

    async def async_step_configure_device(self, user_input=None):
        """Handle input of basic info."""
        errors = {}
        placeholders = {}
        dev_id = self.selected_device
        cloud_devs = self.cloud_data.device_list
        if user_input is not None:
            try:
                self.device_data = user_input.copy()
                self.selected_device: str = dev_id or user_input.get(CONF_DEVICE_ID)
                self.nodeID: str = self.nodeID or user_input.get(CONF_NODE_ID)
                if dev_id is not None:
                    if dev_id in cloud_devs:
                        self.device_data[CONF_MODEL] = cloud_devs[dev_id].get(
                            CONF_PRODUCT_NAME
                        )
                    # Pulls some of device data that aren't required from user in config_flow.
                    if device := self.discovered_devices.get(dev_id):
                        self.device_data[CONF_PRODUCT_KEY] = device.get("productKey")
                        if gateway_id := device.get(CONF_GATEWAY_ID):
                            self.device_data[CONF_GATEWAY_ID] = gateway_id

                # Handle Inputs on edit device mode.
                if self.editing_device:
                    dev_config: dict = self.config_entry.data[CONF_DEVICES].get(
                        dev_id, {}
                    )
                    if self.device_data.pop(EXPORT_CONFIG, False):
                        dev_config = self.config_entry.data[CONF_DEVICES][dev_id].copy()
                        await self.hass.async_add_executor_job(
                            templates.export_config,
                            dev_config,
                            self.device_data[CONF_FRIENDLY_NAME],
                        )
                        return self.async_create_entry(title="", data={})
                    # We will restore device details if it's already existed!
                    for res_conf in [CONF_GATEWAY_ID, CONF_MODEL, CONF_PRODUCT_KEY]:
                        if dev_config.get(res_conf):
                            self.device_data[res_conf] = dev_config.get(res_conf)
                    # Remove the values that assigned as "- or empty space"
                    for rm_conf in [CONF_RESET_DPIDS, CONF_MANUAL_DPS]:
                        if rm_conf in user_input and user_input[rm_conf] in ["-", " "]:
                            self.device_data.pop(rm_conf)

                    self.dps_strings = merge_dps_manual_strings(
                        self.device_data.get(CONF_MANUAL_DPS, ""), self.dps_strings
                    )
                    if self.device_data.pop(CONF_ENABLE_ADD_ENTITIES, False):
                        self.editing_device = False
                        user_input[CONF_DEVICE_ID] = dev_id
                        self.device_data.update(
                            {
                                CONF_DEVICE_ID: dev_id,
                                CONF_NODE_ID: self.nodeID,
                                CONF_DPS_STRINGS: self.dps_strings,
                            }
                        )
                        return await self.async_step_pick_entity_type()

                    self.device_data.update(
                        {
                            CONF_DEVICE_ID: dev_id,
                            CONF_NODE_ID: self.nodeID,
                            CONF_DPS_STRINGS: self.dps_strings,
                            CONF_ENTITIES: [],
                        }
                    )

                    if len(user_input[CONF_ENTITIES]) == 0:
                        # If user unchecked all entities.
                        return self.async_abort(reason="no_entities")

                    if user_input[CONF_ENTITIES]:
                        entity_ids = [
                            int(e.split(":")[0]) for e in user_input[CONF_ENTITIES]
                        ]
                        if self.use_template:
                            device_config = self.template_device
                        else:
                            device_config = self.config_entry.data[CONF_DEVICES][dev_id]
                        self.entities = [
                            entity
                            for entity in device_config[CONF_ENTITIES]
                            if int(entity[CONF_ID]) in entity_ids
                        ]
                        return await self.async_step_configure_entity()

                valid_data = await validate_input(
                    self.hass, self.config_entry.entry_id, user_input
                )
                self.dps_strings = valid_data[CONF_DPS_STRINGS]
                # We will also get protocol version from valid date in case auto used.
                self.device_data[CONF_PROTOCOL_VERSION] = valid_data[
                    CONF_PROTOCOL_VERSION
                ]

                return await self.async_step_device_setup_method()
                # return await self.async_step_pick_entity_type()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except EmptyDpsList:
                errors["base"] = "empty_dps"
            except (OSError, ValueError, pytuya.DecodeError) as ex:
                _LOGGER.debug("Unexpected exception: %s", ex)
                placeholders["ex"] = str(ex)
                errors["base"] = "unknown"
            except Exception as ex:
                _LOGGER.debug("Unexpected exception: %s", ex)
                raise ex

        defaults = {}
        if self.editing_device:
            # If selected device exists as a config entry, load config from it
            defaults = (
                self.device_data
                if self.use_template
                else self.config_entry.data[CONF_DEVICES][dev_id].copy()
            )

            self.nodeID = defaults.get(CONF_NODE_ID, None)
            placeholders["for_device"] = f" for device `{dev_id}`"
            if self.nodeID:
                placeholders.update(
                    {"for_device": f"for Sub-Device `{dev_id}.NodeID {self.nodeID}`"}
                )
            if dev_id in cloud_devs:
                cloud_local_key = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
                if defaults[CONF_LOCAL_KEY] != cloud_local_key:
                    _LOGGER.info(
                        "New local_key detected: new %s vs old %s",
                        cloud_local_key,
                        defaults[CONF_LOCAL_KEY],
                    )
                    defaults[CONF_LOCAL_KEY] = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
                    note = "\nNOTE: a new local_key has been retrieved using cloud API"
                    placeholders = {"for_device": f" for device `{dev_id}`.{note}"}
                    if self.nodeID:
                        placeholders = {
                            "for_device": f" for sub-device `{dev_id}.\nNodeID {self.nodeID}.{note}`"
                        }
            schema = schema_defaults(options_schema(self.entities), **defaults)
        else:
            # user_in will restore input if an error occurred instead of clears all fields.
            user_in = user_input or {}
            defaults[CONF_PROTOCOL_VERSION] = user_in.get(CONF_PROTOCOL_VERSION, "auto")
            defaults[CONF_HOST] = user_in.get(CONF_HOST, "")
            defaults[CONF_DEVICE_ID] = user_in.get(CONF_DEVICE_ID, "")
            defaults[CONF_LOCAL_KEY] = user_in.get(CONF_LOCAL_KEY, "")
            defaults[CONF_FRIENDLY_NAME] = user_in.get(CONF_FRIENDLY_NAME, "")
            defaults[CONF_NODE_ID] = user_in.get(CONF_NODE_ID, "")

            if defaults[CONF_DEVICE_ID] in [cloud_devs, self.selected_device]:
                dev_id = defaults[CONF_DEVICE_ID]

            if dev_id is not None and dev_id in self.discovered_devices:
                # Insert default values from discovery and cloud if present
                device = self.discovered_devices.get(dev_id, {})
                defaults[CONF_HOST] = device.get(CONF_TUYA_IP)
                defaults[CONF_DEVICE_ID] = device.get(CONF_TUYA_GWID)
                defaults[CONF_PROTOCOL_VERSION] = device.get(CONF_TUYA_VERSION)
                defaults[CONF_NODE_ID] = device.get(CONF_NODE_ID, None)

            if dev_id in cloud_devs:
                defaults[CONF_LOCAL_KEY] = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
                defaults[CONF_FRIENDLY_NAME] = cloud_devs[dev_id].get(CONF_NAME)

            schema = schema_defaults(DEVICE_SCHEMA, **defaults)

            placeholders["for_device"] = ""

        return self.async_show_form(
            step_id="configure_device",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_auto_configure_device(self, user_input=None):
        """Handle asking which templates to use"""

        errors = {}
        placeholders = {}

        # Gather the information
        is_cloud = not self.config_entry.data.get(CONF_NO_CLOUD)
        dev_id = self.selected_device
        category = None
        node_id = self.nodeID
        device_data = self.cloud_data.device_list.get(dev_id)
        if device_data:
            category = self.cloud_data.device_list[dev_id].get(TUYA_CATEGORY, "")

        localtuya_data = {
            DEVICE_CLOUD_DATA: device_data,
            CONF_DPS_STRINGS: self.dps_strings,
            CONF_FRIENDLY_NAME: self.device_data.get(CONF_FRIENDLY_NAME),
        }

        dev_data = gen_localtuya_entities(localtuya_data, category)

        # Process to add the device to localtuya HA Config.
        if dev_data:
            self.entities = dev_data
            return await self.async_step_pick_entity_type(
                {NO_ADDITIONAL_ENTITIES: True}
            )

        if not is_cloud:
            err_msg = f"This feature requires cloud API setup for now"
        elif not device_data:
            err_msg = f"Couldn't find your device in the cloud account you using"
        elif not category:
            err_msg = f"Your device category isn't supported"
        elif not dev_data:
            err_msg = f"Couldn't find the data for your device category: {category}."

        placeholders = {"err_msg": err_msg}

        return self.async_show_menu(
            step_id="auto_configure_device",
            menu_options=["device_setup_method"],
            description_placeholders=placeholders,
        )

    async def async_step_pick_entity_type(self, user_input=None):
        """Handle asking if user wants to add another entity."""
        if user_input is not None:
            if user_input.get(NO_ADDITIONAL_ENTITIES):
                config = {
                    **self.device_data,
                    CONF_DPS_STRINGS: self.dps_strings,
                    CONF_ENTITIES: self.entities,
                }

                dev_id = self.device_data.get(CONF_DEVICE_ID)

                new_data = self.config_entry.data.copy()
                new_data[CONF_DEVICES].update({dev_id: config})
                return self._update_entry(new_data)

            if user_input.get(USE_TEMPLATE):
                return await self.async_step_choose_template()

            self.selected_platform = user_input[PLATFORM_TO_ADD]
            return await self.async_step_configure_entity()

        # Add a checkbox that allows bailing out from config flow if at least one
        # entity has been added
        schema = PICK_ENTITY_SCHEMA
        if self.selected_platform is not None:
            schema = schema.extend(
                {vol.Required(NO_ADDITIONAL_ENTITIES, default=True): bool}
            )

        return self.async_show_form(step_id="pick_entity_type", data_schema=schema)

    async def async_step_choose_template(self, user_input=None):
        """Handle asking which templates to use"""
        if user_input is not None:
            self.use_template = True
            filename = user_input.get(TEMPLATES)
            _config = await self.hass.async_add_executor_job(
                templates.import_config, filename
            )
            dev_conf = self.device_data
            dev_conf[CONF_ENTITIES] = _config
            dev_conf[CONF_DPS_STRINGS] = self.dps_strings
            dev_conf[CONF_NODE_ID] = self.nodeID
            self.device_data = dev_conf

            self.entities = dev_conf[CONF_ENTITIES]
            self.template_device = self.device_data
            self.editing_device = True
            return await self.async_step_configure_device()
        templates_list = await self.hass.async_add_executor_job(
            templates.list_templates
        )
        schema = vol.Schema(
            {vol.Required(TEMPLATES): col_to_select(templates_list, custom_value=True)}
        )
        return self.async_show_form(step_id="choose_template", data_schema=schema)

    async def async_step_entity(self, user_input=None):
        """Manage entity settings."""
        errors = {}
        if user_input is not None:
            entity = strip_dps_values(user_input, self.dps_strings)
            entity[CONF_ID] = self.current_entity[CONF_ID]
            entity[CONF_PLATFORM] = self.current_entity[CONF_PLATFORM]
            self.device_data[CONF_ENTITIES].append(entity)
            if len(self.entities) == len(self.device_data[CONF_ENTITIES]):
                return self._update_entry(self.device_data)

        schema = await platform_schema(
            self.hass, self.current_entity[CONF_PLATFORM], self.dps_strings, False
        )
        return self.async_show_form(
            step_id="entity",
            errors=errors,
            data_schema=schema_defaults(
                schema, self.dps_strings, **self.current_entity
            ),
            description_placeholders={
                "id": int(self.current_entity[CONF_ID]),
                "platform": self.current_entity[CONF_PLATFORM],
            },
        )

    async def async_step_configure_entity(self, user_input=None):
        """Manage entity settings."""
        errors = {}
        if user_input is not None:
            if self.editing_device:
                entity = strip_dps_values(user_input, self.dps_strings)
                entity[CONF_ID] = self.current_entity[CONF_ID]
                entity[CONF_PLATFORM] = self.current_entity[CONF_PLATFORM]
                entity[CONF_ICON] = self.current_entity.get(CONF_ICON, "")
                self.device_data[CONF_ENTITIES].append(entity)
                if len(self.entities) == len(self.device_data[CONF_ENTITIES]):
                    # finished editing device. Let's store the new config entry....
                    dev_id = self.device_data[CONF_DEVICE_ID]
                    new_data = self.config_entry.data.copy()
                    entry_id = self.config_entry.entry_id
                    # Removing the unwanted entities.
                    entitesNames = [
                        name.get(CONF_FRIENDLY_NAME)
                        for name in self.device_data[CONF_ENTITIES]
                    ]
                    ent_reg = er.async_get(self.hass)
                    reg_entities = {
                        ent.unique_id: ent.entity_id
                        for ent in er.async_entries_for_config_entry(ent_reg, entry_id)
                        if dev_id in ent.unique_id
                        and ent.original_name not in entitesNames
                    }
                    for entity_id in reg_entities.values():
                        ent_reg.async_remove(entity_id)

                    new_data[CONF_DEVICES][dev_id] = self.device_data
                    return self._update_entry(new_data)
            else:
                user_input[CONF_PLATFORM] = self.selected_platform
                self.entities.append(strip_dps_values(user_input, self.dps_strings))
                # new entity added. Let's check if there are more left...
                user_input = None
                if len(self.available_dps_strings()) == 0:
                    user_input = {NO_ADDITIONAL_ENTITIES: True}
                return await self.async_step_pick_entity_type(user_input)

        if self.editing_device:
            schema = await platform_schema(
                self.hass, self.current_entity[CONF_PLATFORM], self.dps_strings, False
            )
            schema = schema_defaults(schema, self.dps_strings, **self.current_entity)
            placeholders = {
                "entity": f"entity with DP {int(self.current_entity[CONF_ID])}",
                "platform": self.current_entity[CONF_PLATFORM],
            }
        else:
            available_dps = self.available_dps_strings()
            schema = await platform_schema(
                self.hass, self.selected_platform, available_dps
            )
            placeholders = {
                "entity": "an entity",
                "platform": self.selected_platform,
            }

        return self.async_show_form(
            step_id="configure_entity",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_confirm(
        self,
        msg: str,
        confirm_callback: Coroutine = None,
        callback_args: tuple[Any, ...] | None = None,
    ):
        """Create a confirmation config flow page. If submitted, the `confirm_callback` will be called."""
        if confirm_callback:
            if callback_args:
                self._confirm_callback = partial(confirm_callback, *callback_args)
            else:
                self._confirm_callback = confirm_callback

        placeholders = {}
        placeholders["message"] = msg

        if not msg:
            return self._confirm_callback()

        return self.async_show_form(
            step_id="confirm", description_placeholders=placeholders
        )

        # menu = ["confirm", "init"]
        # return self.async_show_menu(
        #     step_id="confirm", menu_options=menu, description_placeholders=placeholders
        # )

    @callback
    def _update_entry(self, new_data, target_obj="", new_title=""):
        """Update entry data and save etnry,"""
        _data = deepcopy(dict(self.config_entry.data))
        if target_obj:
            _data[target_obj].update(new_data)
        else:
            _data.update(new_data)
        _data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

        self.hass.config_entries.async_update_entry(
            self.config_entry, data=_data, title=new_title or self.config_entry.title
        )
        return self.async_create_entry(title=new_title, data={})

    def available_dps_strings(self):
        """Return list of DPs use by the device's entities."""
        available_dps = []
        used_dps = [str(entity[CONF_ID]) for entity in self.entities]
        for dp_string in self.dps_strings:
            dp = dp_string.split(" ")[0]
            if dp not in used_dps:
                available_dps.append(dp_string)
        return available_dps

    @property
    def current_entity(self):
        """Existing configuration for entity currently being edited."""
        return self.entities[len(self.device_data[CONF_ENTITIES])]


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class EmptyDpsList(exceptions.HomeAssistantError):
    """Error to indicate no datapoints found."""


async def setup_localtuya_devices(
    hass: HomeAssistant,
    entry_id: str,
    discovered_devices: dict,
    devices_cloud_data: dict,
    log_fails=False,
):
    """Return a dict of configured devices ready to import into devices data."""
    # Store devices data
    devices_cfg = []
    devices = {}
    fails = {}

    def update_fails(dev_id: str, reason: str, msg: str = None):
        name = devices_cloud_data[dev_id].get(CONF_NAME, dev_id)
        fails.update({dev_id: {"name": name, "reason": reason}})
        if log_fails:
            msg = f"[ name: {name} — id: {dev_id} — reason: {reason or repr(reason)}]"
            _LOGGER.warning(f"Failed to configure device: {msg}")

    # To avoid duplicated entities we will get all devices in every hub.
    entries = hass.config_entries.async_entries(DOMAIN)
    configured_Devices = []
    for entry in entries:
        for devID in entry.data[CONF_DEVICES].keys():
            configured_Devices.append(devID)

    for dev_id, data in discovered_devices.items():
        # Skip configured devices.
        if dev_id in configured_Devices:
            continue
        if dev_cloud_data := devices_cloud_data.get(dev_id):
            # Create localtuya devices data and store them into devices_config.
            device_data = {
                CONF_FRIENDLY_NAME: dev_cloud_data.get(CONF_NAME, dev_id),
                CONF_DEVICE_ID: dev_id,
                CONF_HOST: data[CONF_TUYA_IP],
                CONF_LOCAL_KEY: dev_cloud_data.get(CONF_LOCAL_KEY),
                CONF_PROTOCOL_VERSION: data[CONF_TUYA_VERSION],
                CONF_ENABLE_DEBUG: False,
                CONF_NODE_ID: dev_cloud_data.get(CONF_NODE_ID),
                CONF_MODEL: dev_cloud_data.get(CONF_MODEL),
                CONF_PRODUCT_KEY: data.get("productKey"),
            }
            # If device is sub and has Gateway ID store gatewayID
            if sub_gwid := data.get(CONF_GATEWAY_ID):
                device_data.update({CONF_GATEWAY_ID: sub_gwid})

            # Store device to device_data.
            devices_cfg.append(device_data)

    # Connect to the devices to ensure the are usable.
    validate_devices = [validate_input(hass, entry_id, dev) for dev in devices_cfg]
    results = await asyncio.gather(*validate_devices, return_exceptions=True)

    # Merge test results with devices config
    for i in range(len(results)):
        dev_id = devices_cfg[i].get(CONF_DEVICE_ID)
        if not isinstance(results[i], dict):
            update_fails(dev_id, results[i])
            continue

        devices.update({dev_id: {**devices_cfg[i], **results[i]}})

    # Configure entities.
    for dev_id, dev_data in deepcopy(devices).items():
        category = devices_cloud_data[dev_id].get("category")
        dev_data[DEVICE_CLOUD_DATA] = devices_cloud_data[dev_id]
        if category and (dps_strings := dev_data.get(CONF_DPS_STRINGS, False)):
            dev_entites = gen_localtuya_entities(dev_data, category)

        # Configure entities fails
        if not dev_entites:
            devices.pop(dev_id)
            update_fails(dev_id, f"no configured entities: {dev_entites} - {category}")
            continue

        # Add configured entities
        devices[dev_id].update({CONF_ENTITIES: dev_entites})

    return devices, fails


async def discover_devices() -> tuple[dict[str, dict], dict[str, str]]:
    """Start discovering Tuya devices within the network"""
    errors = {}
    discovered_devices = {}
    try:
        discovered_devices = await discover()
    except OSError as ex:
        if ex.errno == errno.EADDRINUSE:
            errors["base"] = "address_in_use"
        else:
            errors["base"] = "discovery_failed"
    except Exception as ex:
        _LOGGER.exception("discovery failed: %s", ex)
        errors["base"] = "discovery_failed"
    return discovered_devices, errors


def devices_schema(
    discovered_devices, cloud_devices_list, add_custom_device=True, existed_devices={}
):
    """Create schema for devices step."""
    known_devices = {}
    devices = {}
    for dev_id, dev_host in discovered_devices.items():
        dev_name = dev_id
        # when editing devices get INFOS from stored!.
        if not add_custom_device and dev_id in existed_devices.keys():
            dev_name = existed_devices[dev_id].get(CONF_FRIENDLY_NAME, dev_id)
        elif dev_id in cloud_devices_list.keys():
            dev_name = cloud_devices_list[dev_id][CONF_NAME]

            known_devices[f"{dev_name} ({dev_host})"] = dev_id
            continue

        devices[f"{dev_name} ({dev_host})"] = dev_id

    known_devices = dict(sorted(known_devices.items()))
    devices = {**known_devices, **devices}
    if add_custom_device:
        devices.update(CUSTOM_DEVICE)
    else:  # Sort devices in edit mode.
        devices = dict(sorted(devices.items()))

    schema = vol.Schema(
        {
            vol.Required(SELECTED_DEVICE): col_to_select(devices),
        }
    )

    return schema.extend(MASS_CONFIGURE_SCHEMA) if known_devices else schema


def mergeDevicesList(localList: dict, cloudList: dict, addSubDevices=True) -> dict:
    """Merge CloudDevices with Discovered LocalDevices (in specific ways)!"""
    # try Get SubDevices.
    newList = localList.copy()
    for _devID, _devData in cloudList.items():
        try:
            is_online = _devData.get("online", None)
            sub_device = _devData.get(CONF_NODE_ID, False)
            # We skip offline devices and already merged devices.
            if not is_online or _devID in localList:
                continue
            # Make sure the device isn't already in localList.
            if addSubDevices and sub_device:
                # infrared are ir remote sub-devices
                if _devData.get(TUYA_CATEGORY, "").startswith("infrared"):
                    continue

                gateway = get_gateway_by_deviceid(_devID, cloudList)
                local_gw = localList.get(gateway.id)
                if local_gw:
                    # Create a data for sub_device [cloud and local gateway] to merge it with discovered devices.
                    dev_data = {
                        _devID: {
                            CONF_TUYA_IP: local_gw.get(CONF_TUYA_IP),
                            CONF_TUYA_GWID: _devID,
                            CONF_TUYA_VERSION: local_gw.get(CONF_TUYA_VERSION, "auto"),
                            CONF_NODE_ID: _devData.get(CONF_NODE_ID, None),
                            CONF_GATEWAY_ID: local_gw.get(CONF_TUYA_GWID),
                        }
                    }
                    newList.update(dev_data)
        except Exception as ex:
            _LOGGER.debug(f"An error occurred while trying to pull sub-devices {ex}")
            continue
    return newList


def options_schema(entities):
    """Create schema for options."""
    entity_names = [
        f"{entity[CONF_ID]}: {entity[CONF_FRIENDLY_NAME]}" for entity in entities
    ]
    return vol.Schema(
        {
            vol.Required(CONF_FRIENDLY_NAME): cv.string,
            vol.Required(CONF_HOST): cv.string,
            vol.Required(CONF_LOCAL_KEY): cv.string,
            vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): col_to_select(
                sorted(SUPPORTED_PROTOCOL_VERSIONS)
            ),
            vol.Required(CONF_ENABLE_DEBUG, default=False): bool,
            vol.Optional(CONF_SCAN_INTERVAL): int,
            vol.Optional(CONF_MANUAL_DPS): cv.string,
            vol.Optional(CONF_RESET_DPIDS): cv.string,
            vol.Optional(CONF_DEVICE_SLEEP_TIME): int,
            vol.Required(
                CONF_ENTITIES, description={"suggested_value": entity_names}
            ): cv.multi_select(entity_names),
            # col_to_select(entity_names, multi_select=True)
            vol.Required(CONF_ENABLE_ADD_ENTITIES, default=False): bool,
            vol.Optional(EXPORT_CONFIG, default=False): bool,
        }
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


def dps_string_list(dps_data: dict[str, dict], cloud_dp_codes: dict[str, dict]) -> list:
    """Return list of friendly DPS values."""
    strs = []

    # Merge DPs that found through cloud with local.
    for dp, func in cloud_dp_codes.items():
        # Default Manual dp value is -1, we will replace it if it in cloud.
        if dp not in dps_data or dps_data.get(dp) == -1:
            value = func.get("value", "")
            dps_data[dp] = f"{value}, cloud pull"

    for dp, value in dps_data.items():
        if (dp_data := cloud_dp_codes.get(dp)) and (code := dp_data.get("code")):
            strs.append(f"{dp} ( code: {code} , value: {value} )")
        else:
            strs.append(f"{dp} ( value: {value} )")

    return sorted(strs, key=lambda i: int(i.split()[0]))


def gen_dps_strings():
    """Generate list of DPS values."""
    return [f"{dp} (value: ?)" for dp in range(1, 256)]


def strip_dps_values(user_input, dps_strings):
    """Remove values and keep only index for DPS config items."""
    stripped = {}
    for field, value in user_input.items():
        if value in dps_strings:
            stripped[field] = int(user_input[field].split(" ")[0])
        else:
            stripped[field] = user_input[field]
    return stripped


def merge_dps_manual_strings(manual_dps: list, dps_strings: list):
    """Split manual_dps by comma and assign -1 as default value. Return merged with dps string."""
    manual_list = []
    avaliable_dps = [dp.split(" ")[0] for dp in dps_strings]

    for dp in manual_dps.split(","):
        dp = dp.strip()
        if dp.isdigit() and dp not in avaliable_dps and dp != "0":
            manual_list.append(f"{dp} ( value: -1 )")

    return sorted(dps_strings + manual_list, key=lambda i: int(i.split(" ")[0]))


async def platform_schema(
    hass: HomeAssistant, platform, dps_strings, allow_id=True, yaml=False
):
    """Generate input validation schema for a platform."""
    # decide default value of device by platform.
    schema = {}
    if yaml:
        # In YAML mode we force the specified platform to match flow schema
        schema[vol.Required(CONF_PLATFORM)] = col_to_select([platform])
    if allow_id:
        schema[vol.Required(CONF_ID)] = col_to_select(dps_strings, is_dps=True)
    schema[vol.Optional(CONF_FRIENDLY_NAME, default="")] = vol.Any(None, cv.string)
    schema[
        vol.Required(CONF_ENTITY_CATEGORY, default=str(default_category(platform)))
    ] = col_to_select(ENTITY_CATEGORY)

    plat_schema = await hass.async_add_import_executor_job(
        flow_schema, platform, dps_strings
    )

    return vol.Schema(schema).extend(plat_schema)


def default_category(_platform):
    """Auto Select default category depends on the platform."""
    if any(_platform in i for i in DEFAULT_CATEGORIES["CONTROL"]):
        return None
    elif any(_platform in i for i in DEFAULT_CATEGORIES["CONFIG"]):
        return EntityCategory.CONFIG
    elif any(_platform in i for i in DEFAULT_CATEGORIES["DIAGNOSTIC"]):
        return EntityCategory.DIAGNOSTIC
    else:
        return None


def flow_schema(platform, dps_strings):
    """Return flow schema for a specific platform."""
    integration_module = ".".join(__name__.split(".")[:-1])
    return import_module("." + platform, integration_module).flow_schema(dps_strings)


async def validate_input(hass: HomeAssistant, entry_id, data):
    """Validate the user input allows us to connect."""
    logger = pytuya.ContextualLogger()
    logger.set_logger(_LOGGER, data[CONF_DEVICE_ID], True, data[CONF_FRIENDLY_NAME])

    detected_dps = {}
    error = None
    interface = None
    reset_ids = None
    close = True
    bypass_connection = False  # On users risk, only used for low-power power devices
    bypass_handshake = False  # In-case device is passive.

    cid = data.get(CONF_NODE_ID, None)
    localtuya_devices = hass.data[DOMAIN][entry_id].devices
    try:
        conf_protocol = data[CONF_PROTOCOL_VERSION]
        auto_protocol = conf_protocol == "auto"
        # If sub device we will search if gateway is existed if not create new connection.
        if (
            cid
            and (existed_interface := localtuya_devices.get(data[CONF_HOST]))
            and existed_interface.connected
            and not existed_interface.is_connecting
        ):
            interface = existed_interface._interface
            close = False
        else:
            # If 'auto' will be loop through supported protocols.
            for ver in SUPPORTED_PROTOCOL_VERSIONS:
                try:
                    version = ver if auto_protocol else conf_protocol
                    interface = await asyncio.wait_for(
                        pytuya.connect(
                            data[CONF_HOST],
                            data[CONF_DEVICE_ID],
                            data[CONF_LOCAL_KEY],
                            float(version),
                            data[CONF_ENABLE_DEBUG],
                        ),
                        5,
                    )

                    detected_dps = await interface.detect_available_dps(cid=cid)

                    # Break the loop if input isn't auto.
                    if not auto_protocol:
                        break

                    # If Auto: using DPS detected we will assume this is the correct version if dps found.
                    if len(detected_dps) > 0:
                        # Set the conf_protocol to the worked version to return it and update self.device_data.
                        conf_protocol = version
                        break

                # If connection to host is failed raise wrong address.
                except (OSError, ValueError, pytuya.DecodeError) as ex:
                    error = ex
                    break
                except:
                    continue
                finally:
                    if not auto_protocol and data.get(CONF_DEVICE_SLEEP_TIME, 0) > 0:
                        bypass_connection = True
                    if not error and not interface:
                        error = InvalidAuth

        if CONF_RESET_DPIDS in data:
            reset_ids_str = data[CONF_RESET_DPIDS].split(",")
            reset_ids = []
            for reset_id in reset_ids_str:
                reset_ids.append(int(reset_id.strip()))
            logger.debug(
                "Reset DPIDs configured: %s (%s)", data[CONF_RESET_DPIDS], reset_ids
            )
        try:
            # If reset dpids set - then assume reset is needed before status.
            if (reset_ids is not None) and (len(reset_ids) > 0):
                logger.debug("Resetting command for DP IDs: %s", reset_ids)
                # Assume we want to request status updated for the same set of DP_IDs as the reset ones.
                interface.set_updatedps_list(reset_ids)

                # Reset the interface
                await interface.reset(reset_ids, cid=cid)

            # Detect any other non-manual DPS strings
            if not detected_dps:
                detected_dps = await interface.detect_available_dps(cid=cid)

        except (ValueError, pytuya.DecodeError) as ex:
            error = ex
        except Exception as ex:
            logger.debug(f"No DPS able to be detected {ex}")
            detected_dps = {}

        # if manual DPs are set, merge these.
        # detected_dps_device used to prevent user from bypass handshake manual dps.
        detected_dps_device = detected_dps.copy()
        logger.debug("Detected DPS: %s", detected_dps)
        if CONF_MANUAL_DPS in data:
            manual_dps_list = [dps.strip() for dps in data[CONF_MANUAL_DPS].split(",")]
            logger.debug(
                "Manual DPS Setting: %s (%s)", data[CONF_MANUAL_DPS], manual_dps_list
            )
            # merge the lists
            for new_dps in manual_dps_list + (reset_ids or []):
                # If the DPS not in the detected dps list, then add with a
                # default value indicating that it has been manually added
                if str(new_dps) == "0":
                    bypass_handshake = True
                    continue
                if str(new_dps) not in detected_dps:
                    detected_dps[new_dps] = -1

    except (ConnectionRefusedError, ConnectionResetError) as ex:
        raise CannotConnect from ex
    except (OSError, ValueError, pytuya.DecodeError) as ex:
        error = ex
    finally:
        if interface and close:
            await interface.close()

    # Get DP descriptions from the cloud, if the device is there.
    cloud_dp_codes = {}
    cloud_data: TuyaCloudApi = hass.data[DOMAIN][entry_id].cloud_data
    if (dev_id := data.get(CONF_DEVICE_ID)) in cloud_data.device_list:
        cloud_dp_codes = await cloud_data.async_get_device_functions(dev_id)

    # Indicate an error if no datapoints found as the rest of the flow
    # won't work in this case
    if not bypass_connection and error:
        raise error
    # If bypass handshake. otherwise raise failed to make handshake with device.
    # --- Cloud: We will use the DPS found on cloud if exists.
    # --- No cloud: user will have to input the DPS manually.
    if not detected_dps_device and not (
        (cloud_dp_codes or detected_dps) and bypass_handshake
    ):
        raise EmptyDpsList

    logger.debug("Total DPS: %s", detected_dps)
    return {
        CONF_DPS_STRINGS: dps_string_list(detected_dps, cloud_dp_codes),
        CONF_PROTOCOL_VERSION: conf_protocol,
    }


async def attempt_cloud_connection(user_input):
    """Create device."""
    cloud_api = TuyaCloudApi(
        user_input.get(CONF_REGION),
        user_input.get(CONF_CLIENT_ID),
        user_input.get(CONF_CLIENT_SECRET),
        user_input.get(CONF_USER_ID),
    )

    msg, res = await cloud_api.async_connect()

    if res != "ok":
        return cloud_api, {"reason": msg, "msg": res}

    return cloud_api, {}
