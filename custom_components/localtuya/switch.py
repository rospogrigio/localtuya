"""
Simple platform to control LOCALLY Tuya switch devices.

Sample config yaml

switch:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    name: tuya_01
    friendly_name: tuya_01
    protocol_version: 3.3
    switches:
      sw01:
        name: main_plug
        friendly_name: Main Plug
        id: 1
        current: 18
        current_consumption: 19
        voltage: 20
      sw02:
        name: usb_plug
        friendly_name: USB Plug
        id: 7
"""
import logging
import voluptuous as vol

from homeassistant.components.switch import ENTITY_ID_FORMAT, SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import (CONF_HOST, CONF_ID, CONF_SWITCHES, CONF_FRIENDLY_NAME, CONF_ICON, CONF_NAME)
import homeassistant.helpers.config_validation as cv
from time import time, sleep
from threading import Lock

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['pytuya==7.0.8']

CONF_DEVICE_ID = 'device_id'
CONF_LOCAL_KEY = 'local_key'
CONF_PROTOCOL_VERSION = 'protocol_version'
CONF_CURRENT = 'current'
CONF_CURRENT_CONSUMPTION = 'current_consumption'
CONF_VOLTAGE = 'voltage'

DEFAULT_ID = '1'
DEFAULT_PROTOCOL_VERSION = 3.3

ATTR_CURRENT = 'current'
ATTR_CURRENT_CONSUMPTION = 'current_consumption'
ATTR_VOLTAGE = 'voltage'

SWITCH_SCHEMA = vol.Schema({
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Optional(CONF_CURRENT, default='-1'): cv.string,
    vol.Optional(CONF_CURRENT_CONSUMPTION, default='-1'): cv.string,
    vol.Optional(CONF_VOLTAGE, default='-1'): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION): vol.Coerce(float),
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
    vol.Optional(CONF_CURRENT, default='-1'): cv.string,
    vol.Optional(CONF_CURRENT_CONSUMPTION, default='-1'): cv.string,
    vol.Optional(CONF_VOLTAGE, default='-1'): cv.string,
    vol.Optional(CONF_SWITCHES, default={}):
        vol.Schema({cv.slug: SWITCH_SCHEMA}),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    from . import pytuya

    devices = config.get(CONF_SWITCHES)

    switches = []
    pytuyadevice = pytuya.OutletDevice(config.get(CONF_DEVICE_ID), config.get(CONF_HOST), config.get(CONF_LOCAL_KEY))
    pytuyadevice.set_version(float(config.get(CONF_PROTOCOL_VERSION)))

    if len(devices) > 0:
        for object_id, device_config in devices.items():
            dps = {}
            dps[device_config.get(CONF_ID)]=None
            if device_config.get(CONF_CURRENT) != '-1':
                dps[device_config.get(CONF_CURRENT)]=None
            if device_config.get(CONF_CURRENT_CONSUMPTION) != '-1':
                dps[device_config.get(CONF_CURRENT_CONSUMPTION)]=None
            if device_config.get(CONF_VOLTAGE) != '-1':
                dps[device_config.get(CONF_VOLTAGE)]=None
            pytuyadevice.set_dpsUsed(dps)

            outlet_device = TuyaCache(pytuyadevice)
            switches.append(
                    TuyaDevice(
                        outlet_device,
                        device_config.get(CONF_NAME),
                        device_config.get(CONF_FRIENDLY_NAME, object_id),
                        device_config.get(CONF_ICON),
                        device_config.get(CONF_ID),
                        device_config.get(CONF_CURRENT),
                        device_config.get(CONF_CURRENT_CONSUMPTION),
                        device_config.get(CONF_VOLTAGE)
                    )
            )

            print('Setup localtuya subswitch [{}] with device ID [{}] '.format(device_config.get(CONF_FRIENDLY_NAME, object_id), device_config.get(CONF_ID)))
            _LOGGER.info("Setup localtuya subswitch %s with device ID %s ", device_config.get(CONF_FRIENDLY_NAME, object_id), device_config.get(CONF_ID) )
    else:
        dps = {}
        dps[config.get(CONF_ID)]=None
        if config.get(CONF_CURRENT) != '-1':
            dps[config.get(CONF_CURRENT)]=None
        if config.get(CONF_CURRENT_CONSUMPTION) != '-1':
            dps[config.get(CONF_CURRENT_CONSUMPTION)]=None
        if config.get(CONF_VOLTAGE) != '-1':
            dps[config.get(CONF_VOLTAGE)]=None
        pytuyadevice.set_dpsUsed(dps)
        outlet_device = TuyaCache(pytuyadevice)
        switches.append(
                TuyaDevice(
                    outlet_device,
                    config.get(CONF_NAME),
                    config.get(CONF_FRIENDLY_NAME),
                    config.get(CONF_ICON),
                    config.get(CONF_ID),
                    config.get(CONF_CURRENT),
                    config.get(CONF_CURRENT_CONSUMPTION),
                    config.get(CONF_VOLTAGE)
                )
        )

        print('Setup localtuya switch [{}] with device ID [{}] '.format(config.get(CONF_FRIENDLY_NAME), config.get(CONF_ID)))
        _LOGGER.info("Setup localtuya switch %s with device ID %s ", config.get(CONF_FRIENDLY_NAME), config.get(CONF_ID) )

    add_devices(switches)

class TuyaCache:
    """Cache wrapper for pytuya.OutletDevice"""

    def __init__(self, device):
        """Initialize the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        self._device = device
        self._lock = Lock()

    def __get_status(self):
        for i in range(5):
            try:
                status = self._device.status()
                return status
            except Exception:
                print('Failed to update status of device [{}]'.format(self._device.address))
                sleep(1.0)
                if i+1 == 3:
                    _LOGGER.error("Failed to update status of device %s", self._device.address )
#                    return None
                    raise ConnectionError("Failed to update status .")

    def set_status(self, state, switchid):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        for i in range(5):
            try:
                return self._device.set_status(state, switchid)
            except Exception:
                print('Failed to set status of device [{}]'.format(self._device.address))
                if i+1 == 3:
                    _LOGGER.error("Failed to set status of device %s", self._device.address )
                    return
#                    raise ConnectionError("Failed to set status.")

    def status(self):
        """Get state of Tuya switch and cache the results."""
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 15:
                sleep(0.5)
                self._cached_status = self.__get_status()
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()

class TuyaDevice(SwitchDevice):
    """Representation of a Tuya switch."""

    def __init__(self, device, name, friendly_name, icon, switchid, attr_current, attr_consumption, attr_voltage):
        """Initialize the Tuya switch."""
        self._device = device
        self.entity_id =  ENTITY_ID_FORMAT.format(name)
        self._name = friendly_name
        self._icon = icon
        self._switch_id = switchid
        self._attr_current = attr_current
        self._attr_consumption = attr_consumption
        self._attr_voltage = attr_voltage
        self._status = self._device.status()
        self._state = self._status['dps'][self._switch_id]
        print('Initialized tuya switch [{}] with switch status [{}] and state [{}]'.format(self._name, self._status, self._state))

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name


    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def device_state_attributes(self):
        attrs = {}
        try:
            attrs[ATTR_CURRENT] = "{}".format(self._status['dps'][self._attr_current])
            attrs[ATTR_CURRENT_CONSUMPTION] = "{}".format(self._status['dps'][self._attr_consumption]/10)
            attrs[ATTR_VOLTAGE] = "{}".format(self._status['dps'][self._attr_voltage]/10)
#            print('attrs[ATTR_CURRENT]: [{}]'.format(attrs[ATTR_CURRENT]))
#            print('attrs[ATTR_CURRENT_CONSUMPTION]: [{}]'.format(attrs[ATTR_CURRENT_CONSUMPTION]))
#            print('attrs[ATTR_VOLTAGE]: [{}]'.format(attrs[ATTR_VOLTAGE]))

        except KeyError:
            pass
        return attrs

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    def turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        self._device.set_status(True, self._switch_id)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        self._device.set_status(False, self._switch_id)

    def update(self):
        """Get state of Tuya switch."""
        self._status = self._device.status()
        self._state = self._status['dps'][self._switch_id]
