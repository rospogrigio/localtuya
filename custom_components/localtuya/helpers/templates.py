""" Parse templates. """
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


def list_templates():
    dir = os.path.dirname(templates_dir.__file__)
    files = {}
    for p, d, f in os.walk(dir):
        for file in sorted(f):
            if fnmatch(file, "*yaml") or fnmatch(file, "*yml"):
                fn = str(file).replace(".yaml", "").replace("_", " ")
                files[fn.capitalize()] = file
    return files


def create_tuya_config(filename):
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
                    if not isinstance(value, bool) and not isinstance(value, float)
                    else value
                )
            ent[CONF_PLATFORM] = plat
        entity.append(ent)
    return entity


def export_tuya_config(config, config_name):
    export_config = []
    for cfg in config[CONF_ENTITIES]:
        # Special case device_classes
        if CONF_DEVICE_CLASS in cfg.keys():
            cfg[CONF_DEVICE_CLASS] = cfg.get(CONF_DEVICE_CLASS).split("/ /")[0]
        ents = {cfg[CONF_PLATFORM]: cfg}
        export_config.append(ents)
    fname = config_name + ".yaml" if not config_name.endswith(".yaml") else config_name
    fname = fname.replace(" ", "_")
    template_dir = os.path.dirname(templates_dir.__file__)
    template_file = os.path.join(template_dir, fname)
    _config = yaml_dump(export_config, template_file)


def yaml_dump(config, fname: str | None = None) -> JSON_TYPE:
    """Load a YAML file."""
    try:
        with open(fname, "w", encoding="utf-8") as conf_file:
            return yaml.dump(config, conf_file)
    except UnicodeDecodeError as exc:
        _LOGGER.error("Unable to read file %s: %s", fname, exc)
