"""Constants for localtuya integration."""

ATTR_CURRENT = "current"
ATTR_CURRENT_CONSUMPTION = "current_consumption"
ATTR_VOLTAGE = "voltage"

CONF_LOCAL_KEY = "local_key"
CONF_PROTOCOL_VERSION = "protocol_version"
CONF_DPS_STRINGS = "dps_strings"

# switch
CONF_CURRENT = "current"
CONF_CURRENT_CONSUMPTION = "current_consumption"
CONF_VOLTAGE = "voltage"

# cover
CONF_OPENCLOSE_CMDS = "open_close_cmds"
CONF_POSITIONING_MODE = "positioning_mode"
CONF_CURRPOS = "currpos_dps"
CONF_SETPOS = "setpos_dps"
CONF_SPAN_TIME = "span_time"

# sensor
CONF_SCALING = "scaling"

DOMAIN = "localtuya"

# Platforms in this list must support config flows
PLATFORMS = ["binary_sensor", "cover", "fan", "light", "sensor", "switch"]

TUYA_DEVICE = "tuya_device"
