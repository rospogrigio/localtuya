"""Tuya Devices
    This works similar to HA Tuya, is get the category and search for the categories 
    categories data has been modified to works with localtuya

    How to add your device?:
    e.g. Cover device:
        1. make sure your device category isn't exists if you will create new one. you can modifiy existed categories
        2. This configs are main "id" repaired, "icon" opt, "device_class" opt, "state_class" opt, "name" prefer.
        in order to add device you need  to device the localtuya config and the code value:
            example: "3 ( code: percent_state , value: 0 )" <- Download diagnostics from HA Device page.
                current_state_dp=DPCode.PERCENT_STATE < This will map and "percent_state" code to current_state_dp config.

            if the config is not DPS then this will be inserted through "custom_configs" < this used to inject any config into entity config
                example: custom_configs={"positioning_mode": "position"} I hope you got the idea :D
"""


from .base import LocalTuyaEntity, CONF_DPS_STRINGS
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


def generate_tuya_device(localtuya_data: dict, tuya_category: str) -> dict | list:
    """Create localtuya configs using the data that provided from TUYA"""
    detected_dps: list = localtuya_data.get(CONF_DPS_STRINGS)
    device_name: str = localtuya_data.get(CONF_FRIENDLY_NAME).strip()
    ent_data: LocalTuyaEntity

    if not tuya_category or not detected_dps:
        return
    entities = {}

    for platform, tuya_data in DATA_PLATFORMS.items():
        if cat_data := tuya_data.get(tuya_category):
            for ent_data in cat_data:
                main_confs = ent_data.data
                localtuya_conf = ent_data.localtuya_conf
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

                        # used_dp += 1
                if local_entity:
                    # Entity most contains ID
                    if not local_entity.get(CONF_ID):
                        continue
                    # Workaround to Prevent duplicated id.
                    if local_entity[CONF_ID] in entities:
                        continue

                    # Prevent duplicated friendly_name e.g. [switch_switch]
                    # if name := main_confs.get(CONF_FRIENDLY_NAME):
                    #     if name.split()[0].lower() in device_name.split()[-1].lower():
                    #         main_confs[CONF_FRIENDLY_NAME] = ""

                    local_entity.update(main_confs)
                    local_entity[CONF_PLATFORM] = platform
                    entities[local_entity.get(CONF_ID)] = local_entity

    # sort entites by id
    sorted_ids = sorted(entities, key=int)

    # convert to list of configs
    list_entities = [entities.get(id) for id in sorted_ids]

    return list_entities


def parse_enum(dp_code):
    """get enum value if code type is enum"""
    try:
        parsed_dp_code = dp_code.value
    except:
        parsed_dp_code = dp_code

    return parsed_dp_code
