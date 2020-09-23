"""Constants for localtuya integration."""

ATTR_CURRENT = "current"
ATTR_CURRENT_CONSUMPTION = "current_consumption"
ATTR_VOLTAGE = "voltage"

CONF_LOCAL_KEY = "local_key"
CONF_PROTOCOL_VERSION = "protocol_version"
CONF_DPS_STRINGS = "dps_strings"
CONF_YAML_IMPORT = "yaml_import"

# switch
CONF_CURRENT = "current"
CONF_CURRENT_CONSUMPTION = "current_consumption"
CONF_VOLTAGE = "voltage"

# cover
CONF_OPEN_CMD = "open_cmd"
CONF_CLOSE_CMD = "close_cmd"
CONF_STOP_CMD = "stop_cmd"

# sensor
CONF_SCALING = "scaling"

DOMAIN = "localtuya"

# Platforms in this list must support config flows
PLATFORMS = ["cover", "fan", "light", "sensor", "switch"]
