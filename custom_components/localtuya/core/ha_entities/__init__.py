"""
    Tuya Devices: https://xzetsubou.github.io/hass-localtuya/auto_configure/

    This functionality is similar to HA Tuya, as it retrieves the category and searches for the corresponding categories. 
    The categories data has been improved & modified to work seamlessly with localtuya

    Device Data: You can obtain all the data for your device from Home Assistant by directly downloading the diagnostics or using entry diagnostics.
        Alternative: Use Tuya IoT.

    Add a new device or modify an existing one:
        1. Make sure the device category doesn't already exist. If you are creating a new one, you can modify existing categories.
        2. In order to add a device, you need to specify the category of the device you want to add inside the entity type dictionary.
    
    Add entities to devices:
        1. Open the file with the name of the entity type on which you want to make changes [e.g. switches.py] and search for your device category.
        2. You can add entities inside the tuple value of the dictionary by including LocalTuyaEntity and passing the parameters for the entity configurations.
        3. These configurations include "id" (required), "icon" (optional), "device_class" (optional), "state_class" (optional), and "name" (optional) [Using COVERS as an example]
            Example: "3 ( code: percent_state , value: 0 )" - Refer to the Device Data section above for more details.
                current_state_dp = DPCode.PERCENT_STATE < This maps the "percent_state" code DP to the current_state_dp configuration.

            If the configuration is not DPS, it will be inserted through "custom_configs". This is used to inject any configuration into the entity configuration
                Example: custom_configs={"positioning_mode": "position"}. I hope that clarifies the concept
                
        Check URL above for more details. 
"""

import json
from .base import LocalTuyaEntity, CONF_DPS_STRINGS, CLOUD_VALUE, DPType
from enum import Enum
from homeassistant.const import Platform, CONF_FRIENDLY_NAME, CONF_PLATFORM, CONF_ID

import logging

# Supported files
from .alarm_control_panels import ALARMS  # not added yet
from .binary_sensors import BINARY_SENSORS
from .buttons import BUTTONS
from .climates import CLIMATES
from .covers import COVERS
from .fans import FANS
from .humidifiers import HUMIDIFIERS
from .lights import LIGHTS
from .numbers import NUMBERS
from .selects import SELECTS
from .sensors import SENSORS
from .sirens import SIRENS
from .switches import SWITCHES
from .vacuums import VACUUMS

# The supported PLATFORMS [ Platform: Data ]
DATA_PLATFORMS = {
    # Platform.ALARM_CONTROL_PANEL: ALARMS,
    Platform.BINARY_SENSOR: BINARY_SENSORS,
    Platform.BUTTON: BUTTONS,
    Platform.CLIMATE: CLIMATES,
    Platform.COVER: COVERS,
    Platform.FAN: FANS,
    Platform.HUMIDIFIER: HUMIDIFIERS,
    Platform.LIGHT: LIGHTS,
    Platform.NUMBER: NUMBERS,
    Platform.SELECT: SELECTS,
    Platform.SENSOR: SENSORS,
    Platform.SIREN: SIRENS,
    Platform.SWITCH: SWITCHES,
    Platform.VACUUM: VACUUMS,
}

_LOGGER = logging.getLogger(__name__)


def gen_localtuya_entities(localtuya_data: dict, tuya_category: str) -> list[dict]:
    """Return localtuya entities using the data that provided from TUYA"""
    detected_dps: list = localtuya_data.get(CONF_DPS_STRINGS)

    if not tuya_category or not detected_dps:
        _LOGGER.debug(f"Missing category: {tuya_category} or DPS: {detected_dps}")
        return

    device_name: str = localtuya_data.get(CONF_FRIENDLY_NAME).strip()
    device_cloud_data: dict = localtuya_data.get("device_cloud_data", {})
    dps_data = device_cloud_data.get("dps_data", {})

    entities = {}

    for platform, tuya_data in DATA_PLATFORMS.items():
        # TODO: Refactor needed here.
        if cat_data := tuya_data.get(tuya_category):
            for ent_data in cat_data:
                main_confs = ent_data.data
                localtuya_conf = ent_data.localtuya_conf
                localtuya_entity_configs = ent_data.entity_configs
                # Conditions
                contains_any: list[str] = ent_data.contains_any
                local_entity = {}

                # used_dp = 0
                for k, code in localtuya_conf.items():
                    if type(code) == Enum:
                        code = code.value

                    if isinstance(code, tuple):
                        for dp_code in code:
                            if any(dp_code in dps.split() for dps in detected_dps):
                                code = parse_enum(dp_code)
                                break
                            else:
                                code = None

                    for dp_data in detected_dps:
                        dp_data: str = dp_data.lower()

                        if contains_any is not None:
                            if not any(cond in dp_data for cond in contains_any):
                                continue

                        if code and code.lower() in dp_data.split():
                            # Same method we use in config_flow to get dp.
                            local_entity[k] = dp_data.split(" ")[0]

                # Pull dp values from cloud. still unsure to apply this to all.
                # This is due to the fact that some local values may not same with the values provided from cloud.
                # For now, this is applied only to numbers values.
                for k, v in localtuya_entity_configs.items():
                    if isinstance(v, CLOUD_VALUE):
                        config_dp = local_entity.get(v.dp_config)
                        dp_values = get_dp_values(config_dp, dps_data, v) or {}

                        # special case for lights
                        # if v.value_key in dp_values and "kelvin" in k:
                        #     value = dp_values.get(v.value_key)
                        #     dp_values[v.value_key] = convert_to_kelvin(value)

                        local_entity[k] = dp_values.get(v.value_key, v.default_value)
                    else:
                        local_entity[k] = v

                if local_entity:
                    # Entity most contains ID
                    if not local_entity.get(CONF_ID):
                        continue
                    # Workaround to Prevent duplicated id.
                    if local_entity[CONF_ID] in entities:
                        _LOGGER.debug(f"{device_name}: Duplicated ID: {local_entity}")
                        continue

                    local_entity.update(main_confs)
                    local_entity[CONF_PLATFORM] = platform
                    entities[local_entity.get(CONF_ID)] = local_entity
                    _LOGGER.debug(f"{device_name}: Entity configured: {local_entity}")

    # sort entites by id
    sorted_ids = sorted(entities, key=int)

    # convert to list of configs
    list_entities = [entities.get(id) for id in sorted_ids]

    _LOGGER.debug(f"{device_name}: Entities configured: {list_entities}")
    # return []
    return list_entities


def parse_enum(dp_code: Enum) -> str:
    """Get enum value if code type is enum"""
    try:
        parsed_dp_code = dp_code.value
    except:
        parsed_dp_code = dp_code

    return parsed_dp_code


def get_dp_values(dp: str, dps_data: dict, req_info: CLOUD_VALUE = None) -> dict:
    """Get DP Values"""
    if not dp or not dps_data:
        return

    dp_data = dps_data.get(dp, {})
    dp_values = dp_data.get("values")
    dp_type = dp_data.get("type")

    if not dp_values or not (dp_values := json.loads(dp_values)):
        return

    # Integer values: min, max, scale, step
    if dp_values and dp_type == DPType.INTEGER:
        val_scale = dp_values.get("scale", 1)
        dp_values["min"] = scale(dp_values.get("min"), val_scale)
        dp_values["max"] = scale(dp_values.get("max"), val_scale)
        dp_values["step"] = scale(dp_values.get("step"), val_scale, float)
        dp_values["scale"] = scale(1, val_scale, float)
        return dp_values

    # ENUM Values: range: list of values.
    if dp_values and dp_type == DPType.ENUM:
        dp_values["min"] = dp_values.get("range", [])[0]  # first value
        dp_values["max"] = dp_values.get("range", [])[-1]  # Last value
        dp_values["range"] = convert_list(dp_values.get("range"), req_info)
        return dp_values


def scale(value: int, scale: int, _type: type = int) -> float:
    """Return scaled value."""
    return _type(value) / (10**scale)


def convert_list(_list: list, req_info: CLOUD_VALUE = str):
    """Return list to dict values."""
    if not _list:
        return ""

    prefer_type = req_info.prefer_type

    if prefer_type == str:
        # Return str "value1,value2,value3"
        to_str = ",".join(str(v) for v in _list)
        return to_str

    if prefer_type == dict:
        # Return dict {value_1: Value 1, value_2: Value 2, value_3: Value 3}
        to_dict = {}
        for k in _list:
            k_name = k.replace("_", " ").capitalize()  # Default name
            if isinstance(req_info.default_value, dict):
                k_name = req_info.default_value.get(k, k_name)
            if remaped_value := req_info.remap_values.get(k):
                k_name = remaped_value

            if req_info.reverse_dict:
                to_dict.update({k_name: k})
            else:
                to_dict.update({k: k_name})
        return to_dict

    # otherwise return prefer type list
    return _list


def convert_to_kelvin(value):
    """Convert Tuya color temperature to kelvin"""
    # Given data points
    v0, k0 = 0, 2700  # (0, 2700)
    v1, k1 = 1000, 6500  # (1000, 6500)

    # Calculate slope (m) and y-intercept (b) using the given points
    m = (k1 - k0) / (v1 - v0)
    b = k0 - m * v0

    # Use the linear equation to calculate the color temperature (K)
    kelvin = m * value + b

    return kelvin
