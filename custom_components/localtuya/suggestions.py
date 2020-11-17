"""Module used to suggest datapoints for a platform."""
from importlib import import_module

from homeassistant.const import CONF_ID


def _suggest_defaults(suggestions, dps_strings, dps_in_use):
    """Return datapoint suggestions for options."""

    def _match(suggestion):
        for dps_str in dps_strings:
            if dps_str.startswith(f"{suggestion} "):
                return dps_str
        return None

    output = {}
    for conf, conf_suggestion in suggestions.items():
        for suggestion in conf_suggestion:
            # Don't suggest an ID that is already in use
            if conf == CONF_ID and suggestion in dps_in_use:
                continue

            match = _match(suggestion)
            if match:
                output[conf] = match
                break
    return output


def suggest(platform, dps_strings, dps_in_use=None):
    """Suggest datapoints for a platform."""
    integration_module = ".".join(__name__.split(".")[:-1])
    module = import_module("." + platform, integration_module)

    if hasattr(module, "DP_SUGGESTIONS"):
        return _suggest_defaults(module.DP_SUGGESTIONS, dps_strings, dps_in_use or [])
    return {}
