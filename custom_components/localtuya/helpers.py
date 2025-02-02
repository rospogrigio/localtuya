"""
Helpers functions for HASS-LocalTuya.
"""
import logging
import os.path
import yaml

from fnmatch import fnmatch
from homeassistant.util.yaml import load_yaml

from homeassistant.const import (
    CONF_PLATFORM,
    CONF_ENTITIES,
    CONF_DEVICE_CLASS,
)
import custom_components.localtuya.templates as templates_dir

JSON_TYPE = list | dict | str

_LOGGER = logging.getLogger(__name__)


###############################
#          Templates          #
###############################
class templates:
    def list_templates():
        """Return the available templates files."""
        dir = os.path.dirname(templates_dir.__file__)
        files = {}
        for p, d, f in os.walk(dir):
            for file in sorted(f):
                if fnmatch(file, "*yaml") or fnmatch(file, "*yml"):
                    fn = str(file).replace(".yaml", "").replace("_", " ")
                    files[fn.capitalize()] = file
        return files

    def import_config(filename):
        """Create a data that can be used as config in localtuya."""
        template_dir = os.path.dirname(templates_dir.__file__)
        template_file = os.path.join(template_dir, filename)
        _config = load_yaml(template_file)
        entity = []
        for cfg in _config:
            ent = {}
            for plat, values in cfg.items():
                for key, value in values.items():
                    ent[str(key)] = (
                        str(value)
                        if type(value) is not bool and type(value) is not float
                        else value
                    )
                ent[CONF_PLATFORM] = plat
            entity.append(ent)
        return entity

    @classmethod
    def export_config(cls, config, config_name: str):
        """Create a yaml config file for localtuya."""
        export_config = []
        for cfg in config[CONF_ENTITIES]:
            # Special case device_classes
            if CONF_DEVICE_CLASS in cfg.keys():
                cfg[CONF_DEVICE_CLASS] = cfg.get(CONF_DEVICE_CLASS).split("/ /")[0]
            ents = {cfg[CONF_PLATFORM]: cfg}
            export_config.append(ents)
        fname = (
            config_name + ".yaml" if not config_name.endswith(".yaml") else config_name
        )
        fname = fname.replace(" ", "_")
        template_dir = os.path.dirname(templates_dir.__file__)
        template_file = os.path.join(template_dir, fname)
        _config = cls.yaml_dump(export_config, template_file)

    def yaml_dump(config, fname: str | None = None) -> JSON_TYPE:
        """Save yaml config."""
        try:
            with open(fname, "w", encoding="utf-8") as conf_file:
                return yaml.dump(config, conf_file)
        except UnicodeDecodeError as exc:
            _LOGGER.error("Unable to save file %s: %s", fname, exc)


###############################
#         Config Flow         #
###############################
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)


################################
## Global config config flows ##
################################
def _col_to_select(opt_list, multi_select=False, is_dps=False):
    """Convert collections to SelectSelectorConfig."""
    if type(opt_list) == dict:
        return SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=str(v), label=k) for k, v in opt_list.items()
                ],
                mode=SelectSelectorMode.DROPDOWN,
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
                multiple=True if multi_select else False,
            )
        )
