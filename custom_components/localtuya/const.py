"""Constants for localtuya integration."""

DOMAIN = "localtuya"

DATA_DISCOVERY = "discovery"
DATA_CLOUD = "cloud_data"

# Platforms in this list must support config flows
PLATFORMS = [
    "binary_sensor",
    "climate",
    "cover",
    "fan",
    "light",
    "number",
    "select",
    "sensor",
    "switch",
    "vacuum",
]

TUYA_DEVICES = "tuya_devices"

ATTR_CURRENT = "current"
ATTR_CURRENT_CONSUMPTION = "current_consumption"
ATTR_VOLTAGE = "voltage"
ATTR_UPDATED_AT = "updated_at"

# config flow
CONF_LOCAL_KEY = "local_key"
CONF_ENABLE_DEBUG = "enable_debug"
CONF_PROTOCOL_VERSION = "protocol_version"
CONF_DPS_STRINGS = "dps_strings"
CONF_MODEL = "model"
CONF_PRODUCT_KEY = "product_key"
CONF_PRODUCT_NAME = "product_name"
CONF_USER_ID = "user_id"
CONF_ENABLE_ADD_ENTITIES = "add_entities"


CONF_ACTION = "action"
CONF_ADD_DEVICE = "add_device"
CONF_EDIT_DEVICE = "edit_device"
CONF_SETUP_CLOUD = "setup_cloud"
CONF_NO_CLOUD = "no_cloud"
CONF_MANUAL_DPS = "manual_dps_strings"
CONF_DEFAULT_VALUE = "dps_default_value"
CONF_RESET_DPIDS = "reset_dpids"
CONF_PASSIVE_ENTITY = "is_passive_entity"

# light
CONF_BRIGHTNESS_LOWER = "brightness_lower"
CONF_BRIGHTNESS_UPPER = "brightness_upper"
CONF_COLOR = "color"
CONF_COLOR_MODE = "color_mode"
CONF_COLOR_TEMP_MIN_KELVIN = "color_temp_min_kelvin"
CONF_COLOR_TEMP_MAX_KELVIN = "color_temp_max_kelvin"
CONF_COLOR_TEMP_REVERSE = "color_temp_reverse"
CONF_MUSIC_MODE = "music_mode"

# switch
CONF_CURRENT = "current"
CONF_CURRENT_CONSUMPTION = "current_consumption"
CONF_VOLTAGE = "voltage"

# cover
CONF_COMMANDS_SET = "commands_set"
CONF_POSITIONING_MODE = "positioning_mode"
CONF_CURRENT_POSITION_DP = "current_position_dp"
CONF_SET_POSITION_DP = "set_position_dp"
CONF_POSITION_INVERTED = "position_inverted"
CONF_SPAN_TIME = "span_time"

# fan
CONF_FAN_SPEED_CONTROL = "fan_speed_control"
CONF_FAN_OSCILLATING_CONTROL = "fan_oscillating_control"
CONF_FAN_SPEED_MIN = "fan_speed_min"
CONF_FAN_SPEED_MAX = "fan_speed_max"
CONF_FAN_ORDERED_LIST = "fan_speed_ordered_list"
CONF_FAN_DIRECTION = "fan_direction"
CONF_FAN_DIRECTION_FWD = "fan_direction_forward"
CONF_FAN_DIRECTION_REV = "fan_direction_reverse"
CONF_FAN_DPS_TYPE = "fan_dps_type"

# sensor
CONF_SCALING = "scaling"

# climate
CONF_TARGET_TEMPERATURE_DP = "target_temperature_dp"
CONF_CURRENT_TEMPERATURE_DP = "current_temperature_dp"
CONF_TEMPERATURE_STEP = "temperature_step"
CONF_MAX_TEMP_DP = "max_temperature_dp"
CONF_MIN_TEMP_DP = "min_temperature_dp"
CONF_TEMP_MAX = "max_temperature_const"
CONF_TEMP_MIN = "min_temperature_const"
CONF_PRECISION = "precision"
CONF_TARGET_PRECISION = "target_precision"
CONF_HVAC_MODE_DP = "hvac_mode_dp"
CONF_HVAC_MODE_SET = "hvac_mode_set"
CONF_HVAC_FAN_MODE_DP = "hvac_fan_mode_dp"
CONF_HVAC_FAN_MODE_SET = "hvac_fan_mode_set"
CONF_HVAC_SWING_MODE_DP = "hvac_swing_mode_dp"
CONF_HVAC_SWING_MODE_SET = "hvac_swing_mode_set"
CONF_PRESET_DP = "preset_dp"
CONF_PRESET_SET = "preset_set"
CONF_HEURISTIC_ACTION = "heuristic_action"
CONF_HVAC_ACTION_DP = "hvac_action_dp"
CONF_HVAC_ACTION_SET = "hvac_action_set"
CONF_ECO_DP = "eco_dp"
CONF_ECO_VALUE = "eco_value"

# vacuum
CONF_POWERGO_DP = "powergo_dp"
CONF_IDLE_STATUS_VALUE = "idle_status_value"
CONF_RETURNING_STATUS_VALUE = "returning_status_value"
CONF_DOCKED_STATUS_VALUE = "docked_status_value"
CONF_BATTERY_DP = "battery_dp"
CONF_MODE_DP = "mode_dp"
CONF_MODES = "modes"
CONF_FAN_SPEED_DP = "fan_speed_dp"
CONF_FAN_SPEEDS = "fan_speeds"
CONF_CLEAN_TIME_DP = "clean_time_dp"
CONF_CLEAN_AREA_DP = "clean_area_dp"
CONF_CLEAN_RECORD_DP = "clean_record_dp"
CONF_LOCATE_DP = "locate_dp"
CONF_FAULT_DP = "fault_dp"
CONF_PAUSED_STATE = "paused_state"
CONF_RETURN_MODE = "return_mode"
CONF_STOP_STATUS = "stop_status"

# number
CONF_MIN_VALUE = "min_value"
CONF_MAX_VALUE = "max_value"
CONF_STEPSIZE_VALUE = "step_size"

# select
CONF_OPTIONS = "select_options"
CONF_OPTIONS_FRIENDLY = "select_options_friendly"

# States
ATTR_STATE = "raw_state"
CONF_RESTORE_ON_RECONNECT = "restore_on_reconnect"
