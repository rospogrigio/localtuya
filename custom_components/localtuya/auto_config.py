"""Automatic LocalTuya entity inference from Tuya Cloud metadata."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .const import (
    CONF_BRIGHTNESS_LOWER,
    CONF_BRIGHTNESS_UPPER,
    CONF_COLOR,
    CONF_COLOR_MODE,
    CONF_COMMANDS_SET,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_CURRENT_POSITION_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_DIRECTION_INVERTED,
    CONF_ECO_DP,
    CONF_ECO_VALUE,
    CONF_HEURISTIC_ACTION,
    CONF_HVAC_ACTION_DP,
    CONF_HVAC_ACTION_SET,
    CONF_HVAC_FAN_MODE_DP,
    CONF_HVAC_FAN_MODE_SET,
    CONF_HVAC_MODE_DP,
    CONF_HVAC_MODE_SET,
    CONF_PASSIVE_ENTITY,
    CONF_POSITIONING_MODE,
    CONF_POSITION_INVERTED,
    CONF_PRECISION,
    CONF_RESTORE_ON_RECONNECT,
    CONF_SCALING,
    CONF_SET_POSITION_DP,
    CONF_TARGET_PRECISION,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_TEMP_MAX,
    CONF_TEMP_MIN,
    CONF_TEMPERATURE_STEP,
    CONF_VOLTAGE,
)

CONF_BRIGHTNESS = "brightness"
CONF_COLOR_TEMP = "color_temp"
CONF_DEVICE_CLASS = "device_class"
CONF_FRIENDLY_NAME = "friendly_name"
CONF_ID = "id"
CONF_PLATFORM = "platform"
CONF_SCENE = "scene"
CONF_STATE_OFF = "state_off"
CONF_STATE_ON = "state_on"
CONF_TEMPERATURE_UNIT = "temperature_unit"
CONF_UNIT_OF_MEASUREMENT = "unit_of_measurement"

PLATFORM_BINARY_SENSOR = "binary_sensor"
PLATFORM_CLIMATE = "climate"
PLATFORM_COVER = "cover"
PLATFORM_LIGHT = "light"
PLATFORM_SENSOR = "sensor"
PLATFORM_SWITCH = "switch"

COVER_MODE_NONE = "none"
COVER_MODE_POSITION = "position"
COVER_ONOFF_CMDS = "on_off_stop"
COVER_OPENCLOSE_CMDS = "open_close_stop"
COVER_FZZZ_CMDS = "fz_zz_stop"
COVER_12_CMDS = "1_2_3"
COVER_DIRECTION_CODES = (
    "control_back",
    "direction",
    "direction_set",
    "motor_direction",
    "motor_reverse",
    "opposite",
    "reverse",
)
COVER_REVERSE_VALUES = {
    "1",
    "back",
    "backward",
    "inverse",
    "inverted",
    "opposite",
    "reverse",
    "reversed",
    "true",
}

CLIMATE_CATEGORIES = {"qn", "wk", "kt", "rs", "rsd"}
CLIMATE_POWER_CODES = ("power", "switch", "switch_heat", "switch_heater")
CLIMATE_TARGET_TEMP_CODES = (
    "temp_set",
    "target_temp",
    "target_temperature",
    "set_temp",
    "temperature_set",
)
CLIMATE_CURRENT_TEMP_CODES = (
    "temp_current",
    "current_temp",
    "current_temperature",
    "temperature",
    "room_temp",
    "indoor_temp",
    "temp_indoor",
)
CLIMATE_MODE_CODES = ("mode", "work_mode", "heat_mode", "fan_mode")
CLIMATE_ACTION_CODES = ("heat", "heating", "heating_state", "work_state")
CLIMATE_ECO_CODES = ("eco", "eco_mode")
HVAC_TRUE_FALSE_SET = "True/False"
TEMP_UNIT_CELSIUS = "celsius"
TEMP_UNIT_FAHRENHEIT = "fahrenheit"
DEFAULT_CLIMATE_MIN_TEMP = 7
DEFAULT_CLIMATE_MAX_TEMP = 35
CLIMATE_FAN_MODE_NAMES = {
    "auto": "auto",
    "low": "low",
    "middle": "medium",
    "medium": "medium",
    "mid": "medium",
    "high": "high",
    "strong": "top",
    "top": "top",
}
CLIMATE_FAN_MODE_ORDER = ("auto", "low", "medium", "high", "top")

LIGHT_CATEGORIES = {"dj", "dd", "fsd", "dc"}
COVER_CATEGORIES = {"cl", "clkg", "cljqr"}

LIGHT_SWITCH_CODES = ("switch_led", "led_switch", "switch_light", "switch")
LIGHT_BRIGHTNESS_CODES = (
    "bright_value_v2",
    "bright_value",
    "brightness",
    "bright",
)
LIGHT_COLOR_TEMP_CODES = ("temp_value_v2", "temp_value", "colour_temp", "color_temp")
LIGHT_COLOR_CODES = ("colour_data_v2", "colour_data", "color_data")
LIGHT_MODE_CODES = ("work_mode", "mode")
LIGHT_SCENE_CODES = ("scene_data_v2", "scene_data", "scene")

ENERGY_CURRENT_CODES = ("cur_current", "current", "phase_a_current")
ENERGY_POWER_CODES = ("cur_power", "power", "active_power", "phase_a_power")
ENERGY_VOLTAGE_CODES = ("cur_voltage", "voltage", "phase_a_voltage")
ENERGY_SENSOR_CODES = {
    "cur_current",
    "current",
    "phase_a_current",
    "cur_power",
    "power",
    "active_power",
    "phase_a_power",
    "cur_voltage",
    "voltage",
    "phase_a_voltage",
    "add_ele",
    "total_forward_energy",
    "electricity",
}
MOTION_BINARY_CODES = (
    "pir",
    "motion",
    "motion_state",
    "presence",
    "presence_state",
    "occupancy",
    "occupied",
    "human_motion_state",
)
MOTION_ON_VALUES = {
    "1",
    "alarm",
    "detected",
    "motion",
    "motion_detected",
    "occupied",
    "pir",
    "presence",
    "present",
    "true",
}
MOTION_OFF_VALUES = {
    "0",
    "false",
    "no_motion",
    "no_presence",
    "none",
    "normal",
    "not_present",
    "unoccupied",
}

DP_ID_FIELDS = {
    CONF_ID,
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_COLOR,
    CONF_COLOR_MODE,
    CONF_SCENE,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_VOLTAGE,
    CONF_CURRENT_POSITION_DP,
    CONF_SET_POSITION_DP,
    CONF_TARGET_TEMPERATURE_DP,
    CONF_CURRENT_TEMPERATURE_DP,
    CONF_HVAC_MODE_DP,
    CONF_HVAC_FAN_MODE_DP,
    CONF_HVAC_ACTION_DP,
    CONF_ECO_DP,
}


@dataclass(frozen=True)
class AutoConfigResult:
    """Autogenerated entity config and DPS data for one device."""

    entities: list[dict[str, Any]]
    dps_data: dict[int, Any]
    skipped_codes: list[str]


def merge_entity_capabilities(
    existing_entities: list[dict[str, Any]], inferred_entities: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    """Add missing inferred capability fields to matching existing entities."""
    changed = 0
    merged_entities = [entity.copy() for entity in existing_entities]
    inferred_by_key = {
        (entity.get(CONF_PLATFORM), entity.get(CONF_ID)): entity
        for entity in inferred_entities
    }

    for entity in merged_entities:
        inferred = inferred_by_key.get((entity.get(CONF_PLATFORM), entity.get(CONF_ID)))
        if not inferred:
            continue
        for key, value in inferred.items():
            if key not in entity:
                entity[key] = value
                changed += 1

    return merged_entities, changed


def build_dps_data(detected_dps: dict[Any, Any], metadata: dict[str, Any]) -> dict[int, Any]:
    """Merge locally detected DPS values with cloud shadow property values."""
    dps_data: dict[int, Any] = {}
    for dp_id, value in (detected_dps or {}).items():
        parsed_id = _as_int(dp_id)
        if parsed_id is not None:
            dps_data[parsed_id] = value

    for prop in metadata.get("shadow_properties") or []:
        dp_id = _as_int(prop.get("dpId", prop.get("dp_id")))
        if dp_id is not None and dp_id not in dps_data:
            dps_data[dp_id] = prop.get("value", "?")

    return dict(sorted(dps_data.items()))


def build_entities(metadata: dict[str, Any], dps_data: dict[int, Any]) -> AutoConfigResult:
    """Infer LocalTuya entities for a device."""
    device = {**metadata.get("device", {}), **metadata.get("details", {})}
    spec = metadata.get("specifications") or {}
    device_name = device.get("custom_name") or device.get("name") or "Tuya device"
    category = (spec.get("category") or device.get("category") or "").lower()

    code_to_dp = _code_to_dp(metadata)
    specs = _specs_by_code(spec, metadata.get("model"))
    status_codes = set(_codes_from(spec.get("status")))
    function_codes = set(_codes_from(spec.get("functions")))
    used_dp_ids: set[int] = set()
    skipped_codes: list[str] = []
    entities: list[dict[str, Any]] = []

    climate = _build_climate(device_name, category, code_to_dp, specs, dps_data)
    if climate:
        entities.append(climate)
        used_dp_ids.update(_entity_dp_ids(climate))

    cover = _build_cover(device_name, category, code_to_dp, specs, dps_data)
    if cover and not climate:
        entities.append(cover)
        used_dp_ids.update(_entity_dp_ids(cover))

    light = _build_light(device_name, category, code_to_dp, specs, dps_data)
    if light and not cover and not climate:
        entities.append(light)
        used_dp_ids.update(_entity_dp_ids(light))

    switches = []
    if not climate and not light and not cover:
        switches = _build_switches(device_name, code_to_dp, specs, dps_data)
        entities.extend(switches)
        for switch in switches:
            used_dp_ids.update(_entity_dp_ids(switch))

    sensors = _build_sensors(
        device_name,
        code_to_dp,
        specs,
        dps_data,
        used_dp_ids,
        status_codes,
        function_codes,
    )
    entities.extend(sensors)
    for sensor in sensors:
        used_dp_ids.update(_entity_dp_ids(sensor))

    for code, dp_id in code_to_dp.items():
        if dp_id not in used_dp_ids:
            skipped_codes.append(code)

    return AutoConfigResult(entities=entities, dps_data=dps_data, skipped_codes=skipped_codes)


def _build_climate(device_name, category, code_to_dp, specs, dps_data):
    power_dp = _boolean_dp_for(CLIMATE_POWER_CODES, code_to_dp, dps_data, specs)
    target_temp_dp = _numeric_dp_for(
        CLIMATE_TARGET_TEMP_CODES, code_to_dp, dps_data, specs
    )
    current_temp_dp = _numeric_dp_for(
        CLIMATE_CURRENT_TEMP_CODES, code_to_dp, dps_data, specs
    )

    looks_like_climate = category in CLIMATE_CATEGORIES or (
        target_temp_dp and current_temp_dp
    )
    if not power_dp or not target_temp_dp or not looks_like_climate:
        return None

    entity = {
        CONF_ID: power_dp,
        CONF_PLATFORM: PLATFORM_CLIMATE,
        CONF_FRIENDLY_NAME: device_name,
        CONF_TARGET_TEMPERATURE_DP: target_temp_dp,
        CONF_HVAC_MODE_DP: power_dp,
        CONF_HVAC_MODE_SET: HVAC_TRUE_FALSE_SET,
    }
    if current_temp_dp:
        entity[CONF_CURRENT_TEMPERATURE_DP] = current_temp_dp

    _add_temperature_options(
        entity,
        _spec_for_codes(CLIMATE_TARGET_TEMP_CODES, specs),
        _spec_for_codes(CLIMATE_CURRENT_TEMP_CODES, specs),
    )

    mode_spec = _spec_for_codes(CLIMATE_MODE_CODES, specs)
    fan_mode_set = _climate_fan_mode_set(mode_spec)
    mode_dp = _dp_for(CLIMATE_MODE_CODES, code_to_dp, dps_data, specs)
    if (
        mode_dp
        and fan_mode_set
        and (mode_dp not in dps_data or str(dps_data.get(mode_dp)) in fan_mode_set.values())
    ):
        entity[CONF_HVAC_FAN_MODE_DP] = mode_dp
        entity[CONF_HVAC_FAN_MODE_SET] = fan_mode_set

    action_dp = _boolean_dp_for(CLIMATE_ACTION_CODES, code_to_dp, dps_data, specs)
    if action_dp:
        entity[CONF_HVAC_ACTION_DP] = action_dp
        entity[CONF_HVAC_ACTION_SET] = HVAC_TRUE_FALSE_SET
    elif current_temp_dp:
        entity[CONF_HEURISTIC_ACTION] = True

    eco_dp = _boolean_dp_for(CLIMATE_ECO_CODES, code_to_dp, dps_data, specs)
    if eco_dp:
        entity[CONF_ECO_DP] = eco_dp
        entity[CONF_ECO_VALUE] = True

    return entity


def _build_light(device_name, category, code_to_dp, specs, dps_data):
    switch_dp = _dp_for(LIGHT_SWITCH_CODES, code_to_dp, dps_data, specs)
    looks_like_light = category in LIGHT_CATEGORIES or any(
        _dp_for(codes, code_to_dp, dps_data, specs)
        for codes in (
            LIGHT_BRIGHTNESS_CODES,
            LIGHT_COLOR_TEMP_CODES,
            LIGHT_COLOR_CODES,
            LIGHT_MODE_CODES,
        )
    )
    if not switch_dp or not looks_like_light:
        return None

    entity = {
        CONF_ID: switch_dp,
        CONF_PLATFORM: PLATFORM_LIGHT,
        CONF_FRIENDLY_NAME: device_name,
    }
    brightness_dp = _dp_for(LIGHT_BRIGHTNESS_CODES, code_to_dp, dps_data, specs)
    if brightness_dp:
        entity[CONF_BRIGHTNESS] = brightness_dp
        bounds = _integer_bounds(_spec_for_codes(LIGHT_BRIGHTNESS_CODES, specs))
        if bounds:
            entity[CONF_BRIGHTNESS_LOWER], entity[CONF_BRIGHTNESS_UPPER] = bounds

    color_temp_dp = _dp_for(LIGHT_COLOR_TEMP_CODES, code_to_dp, dps_data, specs)
    if color_temp_dp:
        entity[CONF_COLOR_TEMP] = color_temp_dp

    color_dp = _dp_for(LIGHT_COLOR_CODES, code_to_dp, dps_data, specs)
    if color_dp:
        entity[CONF_COLOR] = color_dp

    mode_dp = _dp_for(LIGHT_MODE_CODES, code_to_dp, dps_data, specs)
    if mode_dp:
        entity[CONF_COLOR_MODE] = mode_dp

    scene_dp = _dp_for(LIGHT_SCENE_CODES, code_to_dp, dps_data, specs)
    if scene_dp:
        entity[CONF_SCENE] = scene_dp

    return entity


def _build_switches(device_name, code_to_dp, specs, dps_data):
    switch_codes = [
        code
        for code in code_to_dp
        if re.fullmatch(r"switch(?:_\d+)?", code)
        and _dp_has_value_or_spec(code, code_to_dp[code], dps_data, specs)
        and (
            _is_boolish(dps_data.get(code_to_dp[code]))
            or _is_boolean_spec(specs.get(code, {}))
        )
    ]
    if not switch_codes:
        return []

    energy_config = _energy_config(code_to_dp, dps_data, specs)
    entities = []
    for index, code in enumerate(sorted(switch_codes, key=_switch_sort_key)):
        friendly = device_name if len(switch_codes) == 1 else f"{device_name} {_code_label(code)}"
        entity = {
            CONF_ID: code_to_dp[code],
            CONF_PLATFORM: PLATFORM_SWITCH,
            CONF_FRIENDLY_NAME: friendly,
            CONF_RESTORE_ON_RECONNECT: False,
            CONF_PASSIVE_ENTITY: False,
        }
        if index == 0:
            entity.update(energy_config)
        entities.append(entity)
    return entities


def _build_cover(device_name, category, code_to_dp, specs, dps_data):
    control_code = next(
        (
            code
            for code in ("control", "control_back", "mach_operate")
            if _dp_for((code,), code_to_dp, dps_data, specs)
        ),
        None,
    )
    if not control_code:
        return None

    command_set = _cover_command_set(specs.get(control_code, {}))
    if not command_set and category not in COVER_CATEGORIES:
        return None

    entity = {
        CONF_ID: code_to_dp[control_code],
        CONF_PLATFORM: PLATFORM_COVER,
        CONF_FRIENDLY_NAME: device_name,
        CONF_COMMANDS_SET: command_set or COVER_OPENCLOSE_CMDS,
        CONF_POSITIONING_MODE: COVER_MODE_NONE,
        CONF_POSITION_INVERTED: False,
        CONF_DIRECTION_INVERTED: False,
    }
    if _cover_direction_inverted(code_to_dp, specs, dps_data):
        entity[CONF_POSITION_INVERTED] = True
        entity[CONF_DIRECTION_INVERTED] = True

    current_position = _dp_for(
        ("percent_state", "cur_percent", "position"),
        code_to_dp,
        dps_data,
        specs,
    )
    set_position = _dp_for(
        ("percent_control", "position_set", "set_percent"),
        code_to_dp,
        dps_data,
        specs,
    )
    if current_position and set_position:
        entity[CONF_POSITIONING_MODE] = COVER_MODE_POSITION
        entity[CONF_CURRENT_POSITION_DP] = current_position
        entity[CONF_SET_POSITION_DP] = set_position
    return entity


def _build_sensors(
    device_name,
    code_to_dp,
    specs,
    dps_data,
    used_dp_ids,
    status_codes,
    function_codes,
):
    entities = []
    sensor_dp_ids = set()
    for code, dp_id in sorted(code_to_dp.items(), key=lambda item: item[1]):
        if dp_id in used_dp_ids or dp_id in sensor_dp_ids or not _dp_has_value_or_spec(
            code, dp_id, dps_data, specs
        ):
            continue

        spec = specs.get(code, {})
        code_type = (spec.get("type") or _type_from_value(dps_data.get(dp_id))).lower()
        read_only = _is_read_only(code, spec, status_codes, function_codes)
        energy_sensor = code in ENERGY_SENSOR_CODES
        motion_states = _motion_binary_states(code, code_type, spec, dps_data.get(dp_id))

        if motion_states and read_only:
            state_off, state_on = motion_states
            entities.append(
                {
                    CONF_ID: dp_id,
                    CONF_PLATFORM: PLATFORM_BINARY_SENSOR,
                    CONF_FRIENDLY_NAME: f"{device_name} {_code_label(code)}",
                    CONF_STATE_ON: state_on,
                    CONF_STATE_OFF: state_off,
                    CONF_DEVICE_CLASS: "motion",
                }
            )
            sensor_dp_ids.add(dp_id)
            continue

        if code_type == "boolean" and read_only:
            entities.append(
                {
                    CONF_ID: dp_id,
                    CONF_PLATFORM: PLATFORM_BINARY_SENSOR,
                    CONF_FRIENDLY_NAME: f"{device_name} {_code_label(code)}",
                    CONF_STATE_ON: "True",
                    CONF_STATE_OFF: "False",
                }
            )
            sensor_dp_ids.add(dp_id)
            continue

        if not read_only and not energy_sensor:
            continue

        if code_type not in {"integer", "double", "value", "enum", "string", "raw", "json"}:
            continue

        entity = {
            CONF_ID: dp_id,
            CONF_PLATFORM: PLATFORM_SENSOR,
            CONF_FRIENDLY_NAME: f"{device_name} {_code_label(code)}",
        }
        entity.update(_sensor_metadata(code, spec))
        entities.append(entity)
        sensor_dp_ids.add(dp_id)
    return entities


def _energy_config(code_to_dp, dps_data, specs):
    config = {}
    current = _dp_for(ENERGY_CURRENT_CODES, code_to_dp, dps_data, specs)
    if current:
        config[CONF_CURRENT] = current
    power = _dp_for(ENERGY_POWER_CODES, code_to_dp, dps_data, specs)
    if power:
        config[CONF_CURRENT_CONSUMPTION] = power
    voltage = _dp_for(ENERGY_VOLTAGE_CODES, code_to_dp, dps_data, specs)
    if voltage:
        config[CONF_VOLTAGE] = voltage
    return config


def _climate_fan_mode_set(spec):
    values = _values(spec)
    raw_range = values.get("range") or []
    if not raw_range:
        return {}

    mapping = {}
    for value in raw_range:
        raw_value = str(value)
        ha_mode = CLIMATE_FAN_MODE_NAMES.get(raw_value.lower(), raw_value)
        mapping[ha_mode] = raw_value

    return {
        ha_mode: mapping[ha_mode]
        for ha_mode in CLIMATE_FAN_MODE_ORDER
        if ha_mode in mapping
    } | {
        ha_mode: value
        for ha_mode, value in mapping.items()
        if ha_mode not in CLIMATE_FAN_MODE_ORDER
    }


def _add_temperature_options(entity, target_spec, current_spec):
    target_values = _values(target_spec)
    current_values = _values(current_spec)
    target_precision = _temperature_precision(target_values)
    current_precision = _temperature_precision(current_values)
    bounds = _temperature_bounds(target_values, target_precision)
    step = _temperature_step(target_values, target_precision)
    unit = _temperature_unit(target_values) or _temperature_unit(current_values)

    entity[CONF_TARGET_PRECISION] = target_precision
    entity[CONF_PRECISION] = current_precision
    entity[CONF_TEMPERATURE_STEP] = step
    entity[CONF_TEMP_MIN], entity[CONF_TEMP_MAX] = bounds
    if unit:
        entity[CONF_TEMPERATURE_UNIT] = unit


def _sensor_metadata(code, spec):
    values = _values(spec)
    unit = values.get("unit")
    scale = values.get("scale")
    data: dict[str, Any] = {}
    if unit:
        data[CONF_UNIT_OF_MEASUREMENT] = unit
    if isinstance(scale, int):
        data[CONF_SCALING] = 10 ** (-scale)

    if code in {"cur_voltage", "voltage", "phase_a_voltage"}:
        data.setdefault(CONF_UNIT_OF_MEASUREMENT, "V")
        data.setdefault(CONF_DEVICE_CLASS, "voltage")
        data.setdefault(CONF_SCALING, 0.1)
    elif code in {"cur_current", "current", "phase_a_current"}:
        data.setdefault(CONF_UNIT_OF_MEASUREMENT, "mA")
        data.setdefault(CONF_DEVICE_CLASS, "current")
    elif code in {"cur_power", "power", "active_power", "phase_a_power"}:
        data.setdefault(CONF_UNIT_OF_MEASUREMENT, "W")
        data.setdefault(CONF_DEVICE_CLASS, "power")
        data.setdefault(CONF_SCALING, 0.1)
    elif code in {"add_ele", "total_forward_energy", "electricity"}:
        data.setdefault(CONF_UNIT_OF_MEASUREMENT, "kWh")
        data.setdefault(CONF_DEVICE_CLASS, "energy")
    return data


def _model_properties(model):
    if not isinstance(model, dict):
        return []
    properties = []
    for service in model.get("services") or []:
        properties.extend(service.get("properties") or [])
    return properties


def _model_type_values(type_spec):
    if not isinstance(type_spec, dict):
        return {}
    values = type_spec.copy()
    if "type" not in values:
        return values
    return values


def _code_to_dp(metadata):
    result = {}
    for prop in _model_properties(metadata.get("model")):
        code = prop.get("code")
        dp_id = _as_int(prop.get("abilityId", prop.get("dp_id")))
        if code and dp_id is not None:
            result.setdefault(code, dp_id)
            result.setdefault(_normalize_code(code), dp_id)

    for prop in metadata.get("shadow_properties") or []:
        code = prop.get("code")
        dp_id = _as_int(prop.get("dpId", prop.get("dp_id")))
        if code and dp_id is not None:
            result[code] = dp_id
            result.setdefault(_normalize_code(code), dp_id)
    return result


def _specs_by_code(spec, model=None):
    result = {}
    for item in (spec.get("functions") or []) + (spec.get("status") or []):
        code = item.get("code")
        if not code:
            continue
        values = item.get("values")
        parsed = _parse_values(values)
        normalized_code = _normalize_code(code)
        existing = result.get(normalized_code, result.get(code, {}))
        merged = {**existing, **item}
        if parsed or "values" not in existing:
            merged["values"] = parsed
        else:
            merged["values"] = existing["values"]
        result[code] = merged
        result[normalized_code] = merged

    for prop in _model_properties(model):
        code = prop.get("code")
        if not code:
            continue
        values = _model_type_values(prop.get("typeSpec") or {})
        normalized_code = _normalize_code(code)
        existing = result.get(normalized_code, result.get(code, {}))
        merged = {
            **existing,
            "code": code,
            "type": values.get("type") or prop.get("type"),
            "values": {**existing.get("values", {}), **values},
            "access_mode": prop.get("accessMode"),
        }
        result[code] = merged
        result[normalized_code] = merged
    return result


def _codes_from(items):
    codes = []
    for item in items or []:
        code = item.get("code")
        if not code:
            continue
        codes.append(code)
        codes.append(_normalize_code(code))
    return codes


def _dp_for(codes, code_to_dp, dps_data, specs=None):
    for code in codes:
        dp_id = code_to_dp.get(code)
        if dp_id in dps_data or (
            dp_id is not None and specs is not None and code in specs
        ):
            return dp_id
    return None


def _boolean_dp_for(codes, code_to_dp, dps_data, specs=None):
    for code in codes:
        dp_id = code_to_dp.get(code)
        if dp_id is None:
            continue
        if _is_boolish(dps_data.get(dp_id)) or (
            specs is not None and _is_boolean_spec(specs.get(code, {}))
        ):
            return dp_id
    return None


def _numeric_dp_for(codes, code_to_dp, dps_data, specs=None):
    for code in codes:
        dp_id = code_to_dp.get(code)
        if dp_id is None:
            continue
        if _as_float(dps_data.get(dp_id)) is not None or (
            specs is not None and _is_numeric_spec(specs.get(code, {}))
        ):
            return dp_id
    return None


def _spec_for_codes(codes, specs):
    for code in codes:
        if code in specs:
            return specs[code]
    return {}


def _integer_bounds(spec):
    values = _values(spec)
    lower = _as_int(values.get("min"))
    upper = _as_int(values.get("max"))
    if lower is None or upper is None:
        return None
    return lower, upper


def _cover_command_set(spec):
    values = _values(spec)
    commands = {str(value).lower() for value in values.get("range", [])}
    if {"open", "close", "stop"}.issubset(commands):
        return COVER_OPENCLOSE_CMDS
    if {"on", "off", "stop"}.issubset(commands):
        return COVER_ONOFF_CMDS
    if {"fz", "zz", "stop"}.issubset(commands):
        return COVER_FZZZ_CMDS
    if {"1", "2", "3"}.issubset(commands):
        return COVER_12_CMDS
    return None


def _cover_direction_inverted(code_to_dp, specs, dps_data):
    for code in COVER_DIRECTION_CODES:
        dp_id = code_to_dp.get(code)
        if dp_id is None or dp_id not in dps_data:
            continue
        value = dps_data.get(dp_id)
        if isinstance(value, bool):
            return value
        if _is_numeric_reverse_value(value):
            return True
        if str(value).strip().lower() in COVER_REVERSE_VALUES:
            return True

    return False


def _is_numeric_reverse_value(value):
    try:
        return float(value) == 1
    except (TypeError, ValueError):
        return False


def _values(spec):
    values = spec.get("values") if spec else {}
    if isinstance(values, dict):
        return values
    return {}


def _temperature_precision(values):
    scale = _as_int(values.get("scale"))
    if scale is None:
        return 1
    return 10 ** (-scale)


def _temperature_step(values, precision):
    step = _as_float(values.get("step"))
    if step is None:
        return precision
    return step * precision


def _temperature_bounds(values, precision):
    lower = _as_float(values.get("min"))
    upper = _as_float(values.get("max"))
    if lower is None:
        lower = DEFAULT_CLIMATE_MIN_TEMP
    else:
        lower *= precision
    if upper is None:
        upper = DEFAULT_CLIMATE_MAX_TEMP
    else:
        upper *= precision

    if _temperature_unit(values) == TEMP_UNIT_CELSIUS and upper > 60:
        upper = DEFAULT_CLIMATE_MAX_TEMP
    if lower >= upper:
        lower = DEFAULT_CLIMATE_MIN_TEMP
        upper = DEFAULT_CLIMATE_MAX_TEMP
    return lower, upper


def _temperature_unit(values):
    unit = str(values.get("unit") or "").strip().lower()
    if unit in {"c", "\u2103", "celsius"} or "\u2103" in unit or "celsius" in unit:
        return TEMP_UNIT_CELSIUS
    if unit in {"f", "\u2109", "fahrenheit"} or "\u2109" in unit or "fahrenheit" in unit:
        return TEMP_UNIT_FAHRENHEIT
    return None


def _parse_values(values):
    if isinstance(values, dict):
        return values
    if not values:
        return {}
    try:
        return json.loads(values)
    except (TypeError, ValueError):
        return {}


def _entity_dp_ids(entity):
    return {
        value
        for key, value in entity.items()
        if key in DP_ID_FIELDS and isinstance(value, int) and not isinstance(value, bool)
    }


def _switch_sort_key(code):
    match = re.search(r"_(\d+)$", code)
    return int(match.group(1)) if match else 0


def _code_label(code):
    return code.replace("_", " ").title()


def _type_from_value(value):
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Double"
    return "String"


def _normalize_code(code):
    code = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(code))
    return re.sub(r"[^0-9a-zA-Z]+", "_", code).strip("_").lower()


def _is_boolish(value):
    if isinstance(value, bool):
        return True
    return str(value).lower() in {"true", "false"}


def _dp_has_value_or_spec(code, dp_id, dps_data, specs):
    return dp_id in dps_data or code in specs


def _spec_type(spec):
    values = _values(spec)
    return str(spec.get("type") or values.get("type") or "").lower()


def _is_boolean_spec(spec):
    return _spec_type(spec) in {"bool", "boolean"}


def _is_numeric_spec(spec):
    return _spec_type(spec) in {"double", "float", "integer", "number", "value"}


def _is_read_only(code, spec, status_codes, function_codes):
    access_mode = str(spec.get("access_mode") or "").lower()
    return (
        code in status_codes
        and code not in function_codes
    ) or access_mode in {"r", "ro", "read", "readonly"}


def _motion_binary_states(code, code_type, spec, value):
    if code not in MOTION_BINARY_CODES:
        return None
    if code_type in {"bool", "boolean"}:
        return "False", "True"

    values = _values(spec)
    choices = [str(item) for item in values.get("range", [])]
    if value is not None:
        choices.append(str(value))

    off = next((item for item in choices if item.lower() in MOTION_OFF_VALUES), None)
    on = next((item for item in choices if item.lower() in MOTION_ON_VALUES), None)
    if off and on:
        return off, on
    if on:
        return "none", on
    return None


def _value_in(value, choices):
    return str(value).lower() in choices


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
