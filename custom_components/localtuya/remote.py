"""Platform to present any Tuya DP as a remote."""

import asyncio
import json
import base64
import logging
from functools import partial
from enum import StrEnum
from typing import Any, Iterable
from .config_flow import col_to_select

import voluptuous as vol
from homeassistant.components.remote import (
    ATTR_ACTIVITY,
    ATTR_COMMAND,
    ATTR_COMMAND_TYPE,
    ATTR_NUM_REPEATS,
    ATTR_DELAY_SECS,
    ATTR_DEVICE,
    ATTR_TIMEOUT,
    DOMAIN,
    RemoteEntity,
    RemoteEntityFeature,
)
from homeassistant.components import persistent_notification
from homeassistant.const import STATE_OFF
from homeassistant.core import ServiceCall, State, callback, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, NoEntitySpecifiedError
from homeassistant.helpers.storage import Store

from .entity import LocalTuyaEntity, async_setup_entry
from .const import CONF_RECEIVE_DP, CONF_KEY_STUDY_DP

NSDP_CONTROL = "control"  # The control commands
NSDP_TYPE = "type"  # The identifier of an IR library
NSDP_HEAD = "head"  # Actually used but not documented
NSDP_KEY1 = "key1"  # Actually used but not documented

_LOGGER = logging.getLogger(__name__)


class ControlType(StrEnum):
    ENUM = "Enum"
    JSON = "Json"


class ControlMode(StrEnum):
    SEND_IR = "send_ir"
    STUDY = "study"
    STUDY_EXIT = "study_exit"
    STUDY_KEY = "study_key"


class RemoteDP(StrEnum):
    DP_SEND = "201"
    DP_RECIEVE = "202"


MODE_IR_TO_RF = {
    ControlMode.SEND_IR: "rfstudy_send",
    ControlMode.STUDY: "rf_study",
    ControlMode.STUDY_EXIT: "rfstudy_exit",
    ControlMode.STUDY_KEY: "rf_study",
}

MODE_RF_TO_SHORT = {
    MODE_IR_TO_RF[ControlMode.STUDY]: "rf_shortstudy",
    MODE_IR_TO_RF[ControlMode.STUDY_EXIT]: "rfstudy_exit",
}
ATTR_FEQ = "feq"
ATTR_VER = "ver"
ATTR_RF_TYPE = "rf_type"
ATTR_TIMES = "times"
ATTR_DELAY = "delay"
ATTR_INTERVALS = "intervals"
ATTR_STUDY_FREQ = "study_feq"

RF_DEFAULTS = (
    (ATTR_RF_TYPE, "sub_2g"),
    (ATTR_STUDY_FREQ, "433.92"),
    (ATTR_VER, "2"),
    ("feq", "0"),
    ("rate", "0"),
    ("mode", "0"),
)
SEND_DEFAULTS = (
    (ATTR_TIMES, "6"),
    (ATTR_DELAY, "0"),
    (ATTR_INTERVALS, "0"),
)

CODE_STORAGE_VERSION = 1
SOTRAGE_KEY = "localtuya_remotes_codes"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_RECEIVE_DP, default=RemoteDP.DP_RECIEVE.value): col_to_select(
            dps, is_dps=True
        ),
        vol.Optional(CONF_KEY_STUDY_DP): col_to_select(dps, is_dps=True),
    }


def rf_decode_button(base64_code):
    """Decode base64 RF command."""
    try:
        jstr = base64.b64decode(base64_code)
        jdata: dict = json.loads(jstr)
        return jdata
    except:
        return {}


def parse_head_key(head_key: str):
    """Head and key should looks similar to :HEAD:000:KEY:000. return head, key"""
    head_key = head_key.split(":HEAD:")[-1]
    head = head_key.split(":KEY:")[0]
    key = head_key.split(":KEY:")[1]
    return head, key


class LocalTuyaRemote(LocalTuyaEntity, RemoteEntity):
    """Representation of a Tuya remote."""

    def __init__(
        self,
        device,
        config_entry,
        remoteid,
        **kwargs,
    ):
        """Initialize the Tuya remote."""
        super().__init__(device, config_entry, remoteid, _LOGGER, **kwargs)

        self._dp_send = str(self._config.get(self._dp_id, RemoteDP.DP_SEND))
        self._dp_recieve = str(self._config.get(CONF_RECEIVE_DP, RemoteDP.DP_RECIEVE))
        self._dp_key_study = self._config.get(CONF_KEY_STUDY_DP)

        self._device_id = self._device_config.id
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()

        # self._attr_activity_list: list = []
        # self._attr_current_activity: str | None = None

        self._last_code = None

        self._codes = {}  # Contains only device commands.
        self._global_codes = {}  # contains all devices commands.

        self._codes_storage = Store(self.hass, CODE_STORAGE_VERSION, SOTRAGE_KEY)

        self._storage_loaded = False

        self._attr_supported_features = (
            RemoteEntityFeature.LEARN_COMMAND | RemoteEntityFeature.DELETE_COMMAND
        )

    @property
    def _ir_control_type(self):
        if self.has_config(CONF_KEY_STUDY_DP):
            return ControlType.ENUM
        else:
            return ControlType.JSON

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the remote."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the remote."""
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to a device."""
        if not self._attr_is_on:
            raise ServiceValidationError(f"Remote {self.entity_id} is turned off")

        commands = command
        device = kwargs.get(ATTR_DEVICE)

        repeats: int = kwargs.get(ATTR_NUM_REPEATS)
        repeats_delay: float = kwargs.get(ATTR_DELAY_SECS)

        for req in [device, commands]:
            if not req:
                raise ServiceValidationError("Missing required fields")

        if not self._storage_loaded:
            await self._async_load_storage()

        # base64_code = ""
        # if base64_code is None:
        #     option_value = ""
        #     _LOGGER.debug("Sending Option: -> " + option_value)

        #     pulses = self.pronto_to_pulses(option_value)
        #     base64_code = "1" + self.pulses_to_base64(pulses)
        for command in commands:
            code = self._get_code(device, command)

            base64_code = code
            if repeats:
                current_repeat = 0
                while current_repeat < repeats:
                    await self.send_signal(ControlMode.SEND_IR, base64_code)
                    if repeats_delay:
                        await asyncio.sleep(repeats_delay)
                    current_repeat += 1
                continue

            await self.send_signal(ControlMode.SEND_IR, base64_code)

    async def async_learn_command(self, **kwargs: Any) -> None:
        """Learn a command from a device."""
        if not self._attr_is_on:
            raise ServiceValidationError(f"Remote {self.entity_id} is turned off")

        now, timeout = 0, kwargs.get(ATTR_TIMEOUT, 30)

        device = kwargs.get(ATTR_DEVICE)
        commands = kwargs.get(ATTR_COMMAND)

        is_rf = kwargs.get(ATTR_COMMAND_TYPE) == "rf"
        # command_type = kwargs.get(ATTR_COMMAND_TYPE)
        for req in [device, commands]:
            if not req:
                raise ServiceValidationError("Missing required fields")

        if not self._storage_loaded:
            await self._async_load_storage()

        if self._lock.locked():
            return self.debug("The device is already in learning mode.")

        async with self._lock:
            for command in commands:
                await self.send_signal(ControlMode.STUDY, rf=is_rf)
                persistent_notification.async_create(
                    self.hass,
                    f"Press the '{command}' button.",
                    title="Learn command",
                    notification_id="learn_command",
                )

                try:
                    self.debug(f"Waiting for code from DP: {self._dp_recieve}")
                    await asyncio.wait_for(self._event.wait(), timeout)
                    await self.save_new_command(device, command, self._last_code)
                except TimeoutError:
                    raise ServiceValidationError(f"Timeout: Failed to learn: {command}")
                finally:
                    self._event.clear()
                    await self.send_signal(ControlMode.STUDY_EXIT, rf=is_rf)
                    persistent_notification.async_dismiss(
                        self.hass, notification_id="learn_command"
                    )

                # code retrieve success and it's stored in self._last_code
                # we will store the codes.

                if command != commands[-1]:
                    await asyncio.sleep(1)

    async def async_delete_command(self, **kwargs: Any) -> None:
        """Delete commands from the database."""
        device = kwargs.get(ATTR_DEVICE)
        commands = kwargs.get(ATTR_COMMAND)

        for req in [device, commands]:
            if not req:
                raise ServiceValidationError("Missing required fields")

        if not self._storage_loaded:
            await self._async_load_storage()

        for command in commands:
            await self._delete_command(device, command)

    async def send_signal(self, control, base64_code=None, rf=False):
        """Send command to the remote device."""
        rf_data = rf_decode_button(base64_code)
        is_rf = rf_data or rf

        @callback
        def async_handle_enum_type():
            """Handle enum type IR."""
            commands = {self._dp_id: control, "13": 0}
            if control == ControlMode.SEND_IR:
                if all(i in base64_code for i in (":HEAD:", ":KEY:")):
                    head, key = parse_head_key(base64_code)
                    commands["3"] = head
                    commands["4"] = key
                else:
                    commands[self._dp_id] = ControlMode.STUDY_KEY.value
                    commands[self._dp_key_study] = base64_code
            return commands

        @callback
        def async_handle_json_type():
            """Handle json type IR."""
            commands = {NSDP_CONTROL: control}
            if control == ControlMode.SEND_IR:
                commands[NSDP_TYPE] = 0
                if all(i in base64_code for i in (":HEAD:", ":KEY:")):
                    head, key = parse_head_key(base64_code)
                    commands[NSDP_HEAD] = head
                    commands[NSDP_KEY1] = key
                else:
                    commands[NSDP_HEAD] = ""
                    commands[NSDP_KEY1] = "1" + base64_code
            return commands

        @callback
        def async_handle_rf_json_type():
            """Handle json type RF."""
            commands = {NSDP_CONTROL: MODE_IR_TO_RF[control]}
            if freq := rf_data.get(ATTR_STUDY_FREQ):
                commands[ATTR_STUDY_FREQ] = freq
            if ver := rf_data.get(ATTR_VER):
                commands[ATTR_VER] = ver

            for attr, default_value in RF_DEFAULTS:
                if attr not in commands:
                    commands[attr] = default_value

            if control == ControlMode.SEND_IR:
                commands[NSDP_KEY1] = {"code": base64_code}
                for attr, default_value in SEND_DEFAULTS:
                    if attr not in commands[NSDP_KEY1]:
                        commands[NSDP_KEY1][attr] = default_value
            return commands

        if self._ir_control_type == ControlType.ENUM:
            commands = async_handle_enum_type()
        else:
            if is_rf:
                commands = async_handle_rf_json_type()
            else:
                commands = async_handle_json_type()
            commands = {self._dp_id: json.dumps(commands)}

        self.debug(f"Sending Command: {commands}")
        if rf_data:
            self.debug(f"Decoded RF Button: {rf_data}")

        await self._device.set_dps(commands)

    async def _delete_command(self, device, command) -> None:
        """Store new code into stoarge."""
        codes_data = self._codes
        ir_controller = self._device_id
        devices_data = self._global_codes

        if ir_controller in codes_data and device in codes_data[ir_controller]:
            devices_data = codes_data[ir_controller]

        if device not in devices_data:
            raise ServiceValidationError(
                f"Couldn't find the device: {device} available devices is on this IR Remote is: {list(devices_data)}."
            )

        commands = devices_data[device]
        if command not in commands:
            commands.pop("rf", False)
            raise ServiceValidationError(
                f"Couldn't find the command {command} for in {device} device. the available commands for this device is: {list(commands)}"
            )

        # For now this only works if the command is in the list of commands of this device.
        devices_data[device].pop(command)
        if device in self._global_codes:
            self._global_codes.pop(device)
        await self._codes_storage.async_save(codes_data)

    async def save_new_command(self, device, command, code) -> None:
        """Store new code into stoarge."""
        if not self._storage_loaded:
            await self._async_load_storage()

        device_unqiue_id = self._device_id
        codes = self._codes

        if device_unqiue_id not in codes:
            codes[device_unqiue_id] = {}

        # device_data = {command: {ATTR_COMMAND: code, ATTR_COMMAND_TYPE: command_type}}
        device_data = {command: code}

        if device in codes[device_unqiue_id]:
            codes[device_unqiue_id][device].update(device_data)
        else:
            codes[device_unqiue_id][device] = device_data

        self._global_codes[device] = device_data
        await self._codes_storage.async_save(codes)

    async def _async_load_storage(self):
        """Load code and flag storage from disk."""
        # Exception is intentionally not trapped to
        # provide feedback if something fails.
        # await self._codes_storage._async_migrate_func(1, 1, self._codes)
        self._codes.update(await self._codes_storage.async_load() or {})

        if self._codes:
            for dev in self._codes.keys():
                self._global_codes.update(self._codes[dev])

        self._storage_loaded = True

    # No need to restore state for a remote
    async def restore_state_when_connected(self):
        """Do nothing for a remote."""
        return

    def _get_code(self, device, command):
        """Get the code of command from database."""
        codes_data = self._codes
        ir_controller = self._device_id
        devices_data = self._global_codes

        if ir_controller in codes_data and device in codes_data[ir_controller]:
            devices_data = codes_data[ir_controller]

        if device not in devices_data:
            raise ServiceValidationError(
                f"Couldn't find the device: {device} available devices is on this IR Remote is: {list(devices_data)}."
            )

        commands = devices_data[device]
        if command not in commands:
            commands.pop("rf", False)
            raise ServiceValidationError(
                f"Couldn't find the command {command} for in {device} device. the available commands for this device is: {list(commands)}"
            )

        command = devices_data[device][command]

        return command

    async def _async_migrate_func(self, old_major_version, old_minor_version, old_data):
        """Migrate to the new version."""
        raise NotImplementedError

    def status_updated(self):
        """Device status was updated."""
        state = self.dp_value(self._dp_id)
        if (dp_recv := self.dp_value(self._dp_recieve)) != self._last_code:
            self._last_code = dp_recv
            self._event.set()

    def status_restored(self, stored_state: State) -> None:
        """Device status was restored.."""
        state = stored_state
        self._attr_is_on = state is None or state.state != STATE_OFF


async def async_setup_services(hass: HomeAssistant, entities: list[LocalTuyaRemote]):
    """Setup remote services."""

    async def _handle_add_key(call: ServiceCall):
        """Handle add remote key service's action."""
        entity = None
        for ent in entities:
            if call.data.get("target") == ent.device_entry.id:
                entity = ent
        if not entity:
            raise NoEntitySpecifiedError("The targeted device could not be found")

        if base65code := call.data.get("base64"):
            await entity.save_new_command(
                call.data["device_name"], call.data["command_name"], base65code
            )
        elif (head := call.data.get("head")) and (key := call.data.get("key")):
            base65code = f":HEAD:{head}:KEY:{key}"
            await entity.save_new_command(
                call.data["device_name"], call.data["command_name"], base65code
            )
        else:
            raise ServiceValidationError(
                "Ensure that the fields for Raw Base64 code or header/key are valid"
            )

    hass.services.async_register("localtuya", "remote_add_code", _handle_add_key)


async_setup_entry = partial(
    async_setup_entry,
    DOMAIN,
    LocalTuyaRemote,
    flow_schema,
    async_setup_services=async_setup_services,
)
