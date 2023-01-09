"""Platform to present any Tuya DP as an enumeration."""
import logging
from functools import partial
import base64
import json
import struct
import voluptuous as vol
from homeassistant.components.button import DOMAIN, ButtonEntity
from homeassistant.const import (
    CONF_DEVICE_CLASS    
)

from .common import LocalTuyaEntity, async_setup_entry

from .const import (CONF_IR_BUTTON, CONF_IR_BUTTON_FRIENDLY, CONF_IR_DP_ID)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_IR_BUTTON): str,
        vol.Required(CONF_IR_BUTTON_FRIENDLY): str,
        vol.Required(CONF_IR_DP_ID): str,
    }


_LOGGER = logging.getLogger(__name__)
NSDP_CONTROL = "control"       # The control commands
NSDP_TYPE = "type"             # The identifier of an IR library
NSDP_HEAD = "head"             # Actually used but not documented
NSDP_KEY1 = "key1"             # Actually used but not documented

class LocaltuyaIRButton(LocalTuyaEntity, ButtonEntity):
    """Representation of a Tuya Enumeration."""
    
    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        dp_list = device.dps_to_request
        generic_list = {}
        for dp in list(dp_list):
            generic_list[str(dp)] = "generic"
        
        self._status = generic_list
        self._default_status = generic_list
        
        device._bypass_status = True
        device._default_status = generic_list

        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
                
        self._state = None
        self._button_pronto = self._config.get(CONF_IR_BUTTON)
        self._default_dp = self._config.get(CONF_IR_DP_ID)

        # Set Display options
        self._display_options = []
        display_options_str = ""
        if CONF_IR_BUTTON_FRIENDLY in self._config:
            display_options_str = self._config.get(CONF_IR_BUTTON_FRIENDLY).strip()

        _LOGGER.debug("Button Configured: %s", display_options_str)
        
        self._display_options.append(display_options_str)
        _LOGGER.debug(
            "Button Pronto Code: %s - Button Friendly: %s",
            str(self._button_pronto),
            str(self._display_options),
        )

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_press(self) -> None:
        """Update the current value."""
        option_value = self._button_pronto
        _LOGGER.debug("Sending Option: -> " + option_value)

        pulses = self.pronto_to_pulses(option_value)
        base64_code = self.pulses_to_base64(pulses)

        await self.send_signal(base64_code)
        
    def status_updated(self):
        """Device status was updated."""
        super().status_updated()        
        self._status = self._default_status 
        self._state_friendly = "Generic Working"

    # Default value is the first option
    def entity_default_value(self):
        """Return the first option as the default value for this entity type."""
        return self._button_pronto

    '''
    * Here Starts the journy of converting from pronto to a true IR Signal
    '''

    async def send_signal(self, base64_code):
        command = {
            NSDP_CONTROL: "send_ir",
            NSDP_TYPE: 0,
        }
        command[NSDP_HEAD] = ''
        command[NSDP_KEY1] = '1' + base64_code

        await self._device.set_dp(json.dumps(command), self._default_dp)

    def pronto_to_pulses(self, pronto):
        ret = [ ]
        pronto = [int(x, 16) for x in pronto.split(' ')]
        ptype = pronto[0]
        timebase = pronto[1]
        pair1_len = pronto[2]
        pair2_len = pronto[3]
        if ptype != 0:
            # only raw (learned) codes are handled
            return ret
        if timebase < 90 or timebase > 139:
            # only 38 kHz is supported?
            return ret
        pronto = pronto[4:]
        timebase *= 0.241246
        for i in range(0, pair1_len*2, 2):
            ret += [round(pronto[i] * timebase), round(pronto[i+1] * timebase)]
        pronto = pronto[pair1_len*2:]
        for i in range(0, pair2_len*2, 2):
            ret += [round(pronto[i] * timebase), round(pronto[i+1] * timebase)]
        return ret

    def pulses_to_base64(self, pulses):
        fmt = '<' + str(len(pulses)) + 'H'
        return base64.b64encode( struct.pack(fmt, *pulses) ).decode("ascii")


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaIRButton, flow_schema)
