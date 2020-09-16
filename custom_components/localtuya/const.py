"""Constants for localtuya integration."""

ATTR_CURRENT = 'current'
ATTR_CURRENT_CONSUMPTION = 'current_consumption'
ATTR_VOLTAGE = 'voltage'

CONF_LOCAL_KEY = "local_key"
CONF_PROTOCOL_VERSION = "protocol_version"
CONF_DPS_STRINGS = "dps_strings"
CONF_YAML_IMPORT = "yaml_import"

# switch
CONF_CURRENT = "current"
CONF_CURRENT_CONSUMPTION = "current_consumption"
CONF_VOLTAGE = "voltage"

# cover
ATTR_OPEN_CMD = "open_cmd"
ATTR_CLOSE_CMD = "close_cmd"
ATTR_STOP_CMD = "stop_cmd"
ATTR_GET_POSITION_KEY = "get_position_key"
ATTR_SET_POSITION_KEY = "set_position_key"
CONF_OPEN_CMD = "open_cmd"
CONF_CLOSE_CMD = "close_cmd"
CONF_STOP_CMD = "stop_cmd"
CONF_GET_POSITION_KEY = "get_position_key"
CONF_SET_POSITION_KEY = "set_position_key"
CONF_COVER_COMMAND_KEY = "cover_command_key"
CONF_LAST_MOVEMENT_KEY = "last_movement_key"

DOMAIN = "localtuya"

# Platforms in this list must support config flows
PLATFORMS = ["cover", "fan", "light", "switch"]
