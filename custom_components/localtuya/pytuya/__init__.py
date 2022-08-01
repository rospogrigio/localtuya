# PyTuya Module
# -*- coding: utf-8 -*-
"""
Python module to interface with Tuya WiFi, Zigbee, or Bluetooth smart devices.

Mostly derived from Shenzhen Xenon ESP8266MOD WiFi smart devices
E.g. https://wikidevi.com/wiki/Xenon_SM-PW701U

Author: clach04
Maintained by: postlund

For more information see https://github.com/clach04/python-tuya

Classes
   TuyaProtocol(dev_id, local_key, protocol_version, on_connected, listener, is_gateway)
       dev_id (str): Device ID e.g. 01234567891234567890
       local_key (str): The encryption key, obtainable via iot.tuya.com
       protocol_version (float): The protocol version (3.1 or 3.3).
       on_connected (object): Callback when connected.
       listener (object): Listener for events such as status updates.
       is_gateway (bool): Specifies if this is a gateway.

Functions
   json = status()               # returns json payload for current dps status
   detect_available_dps()        # returns a list of available dps provided by the device
   update_dps(dps)               # sends update dps command
   add_dps_to_request(dp_index, cid)  # adds dp_index to the list of dps used by the
                                      # device (to be queried in the payload), optionally
                                      # with sub-device cid if this is a gateway
   set_dp(on, dp_index, cid)     # Set value of any dps index, optionally with cid if this is a gateway
   set_dps(dps, cid)             # Set values of a set of dps, optionally with cid if this is a gateway
   add_sub_device(cid)           # Adds a sub-device to a gateway
   remove_sub_device(cid)        # Removes a sub-device

Credits
 * TuyaAPI https://github.com/codetheweb/tuyapi by codetheweb and blackrozes
   For protocol reverse engineering
 * PyTuya https://github.com/clach04/python-tuya by clach04
   The origin of this python module (now abandoned)
 * LocalTuya https://github.com/rospogrigio/localtuya-homeassistant by rospogrigio
   Updated pytuya to support devices with Device IDs of 22 characters
"""

import asyncio
import base64
import binascii
import json
import logging
import struct
import time
import weakref
from abc import ABC, abstractmethod
from collections import namedtuple
from hashlib import md5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

version_tuple = (9, 0, 0)
version = version_string = __version__ = "%d.%d.%d" % version_tuple
__author__ = "postlund"

_LOGGER = logging.getLogger(__name__)

TuyaMessage = namedtuple("TuyaMessage", "seqno cmd retcode payload crc crcpassed")

ACTION_SET = "set"
ACTION_STATUS = "status"
ACTION_HEARTBEAT = "heartbeat"
ACTION_UPDATEDPS = "updatedps"  # Request refresh of DPS

PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"

PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + 12 * b"\x00"

MESSAGE_HEADER_FMT = ">4I"  # 4*uint32: prefix, seqno, cmd, length
MESSAGE_RECV_HEADER_FMT = ">5I"  # 4*uint32: prefix, seqno, cmd, length, retcode
MESSAGE_END_FMT = ">2I"  # 2*uint32: crc, suffix

PREFIX_VALUE = 0x000055AA
SUFFIX_VALUE = 0x0000AA55

HEARTBEAT_INTERVAL = 10

# DPS that are known to be safe to use with update_dps (0x12) command
UPDATE_DPS_WHITELIST = [18, 19, 20]  # Socket (Wi-Fi)

DEV_TYPE_0A = "type_0a"  # DP_QUERY
DEV_TYPE_0D = "type_0d"  # CONTROL_NEW

COMMAND_DP_QUERY = 0x0A
COMMAND_CONTROL_NEW = 0x0D
COMMAND_SET = 0x07
PUSH_STATUS = 0x08
COMMAND_HEARTBEAT = 0x09
COMMAND_DP_QUERY_NEW = 0x10
COMMAND_UPDATE_DPS = 0x12

# This is intended to match requests.json payload at
# https://github.com/codetheweb/tuyapi :
# type_0a devices require the 0a command as the status request
# type_0d devices require the 0d command as the status request, and the list of
# dps used set to null in the request payload (see generate_payload method)

# prefix: # Next byte is command byte ("hexByte") some zero padding, then length
# of remaining payload, i.e. command + suffix (unclear if multiple bytes used for
# length, zero padding implies could be more than one byte)
GATEWAY_PAYLOAD_DICT = {
    # TYPE_0A should never be used with gateways
    DEV_TYPE_0D: {
        ACTION_STATUS: {"hexByte": COMMAND_DP_QUERY_NEW, "command": {"cid": ""}},
        ACTION_SET: {"hexByte": COMMAND_CONTROL_NEW, "command": {"cid": "", "t": ""}},
        ACTION_HEARTBEAT: {"hexByte": COMMAND_HEARTBEAT, "command": {}},
    },
}
PAYLOAD_DICT = {
    DEV_TYPE_0A: {
        ACTION_STATUS: {"hexByte": COMMAND_DP_QUERY, "command": {"gwId": "", "devId": "", "uid": ""}},
        ACTION_SET: {"hexByte": COMMAND_SET, "command": {"devId": "", "uid": "", "t": ""}},
        ACTION_HEARTBEAT: {"hexByte": COMMAND_HEARTBEAT, "command": {}},
        ACTION_UPDATEDPS: {"hexByte": COMMAND_UPDATE_DPS, "command": {"dpId": [18, 19, 20]}},
    },
    DEV_TYPE_0D: {
        ACTION_STATUS: {"hexByte": COMMAND_DP_QUERY_NEW, "command": {"gwId": "", "devId": "", "uid": ""}},
        ACTION_SET: {"hexByte": COMMAND_SET, "command": {"devId": "", "uid": "", "t": ""}},
        ACTION_HEARTBEAT: {"hexByte": COMMAND_HEARTBEAT, "command": {}},
        ACTION_UPDATEDPS: {"hexByte": COMMAND_UPDATE_DPS, "command": {"dpId": [18, 19, 20]}},
    },
}


class TuyaLoggingAdapter(logging.LoggerAdapter):
    """Adapter that adds device id to all log points."""

    def process(self, msg, kwargs):
        """Process log point and return output."""
        dev_id = self.extra["device_id"]
        return f"[{dev_id[0:3]}...{dev_id[-3:]}] {msg}", kwargs


class ContextualLogger:
    """Contextual logger adding device id to log points."""

    def __init__(self):
        """Initialize a new ContextualLogger."""
        self._logger = None

    def set_logger(self, logger, device_id):
        """Set base logger to use."""
        self._logger = TuyaLoggingAdapter(logger, {"device_id": device_id})

    def debug(self, msg, *args):
        """Debug level log."""
        return self._logger.log(logging.DEBUG, msg, *args)

    def info(self, msg, *args):
        """Info level log."""
        return self._logger.log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """Warning method log."""
        return self._logger.log(logging.WARNING, msg, *args)

    def error(self, msg, *args):
        """Error level log."""
        return self._logger.log(logging.ERROR, msg, *args)

    def exception(self, msg, *args):
        """Exception level log."""
        return self._logger.exception(msg, *args)


def pack_message(msg):
    """Pack a TuyaMessage into bytes."""
    # Create full message excluding CRC and suffix
    buffer = (
            struct.pack(
                MESSAGE_HEADER_FMT,
                PREFIX_VALUE,
                msg.seqno,
                msg.cmd,
                len(msg.payload) + struct.calcsize(MESSAGE_END_FMT),
                )
            + msg.payload
    )

    # Calculate CRC, add it together with suffix
    buffer += struct.pack(MESSAGE_END_FMT, binascii.crc32(buffer), SUFFIX_VALUE)

    return buffer


class AESCipher:
    """Cipher module for Tuya communication."""

    def __init__(self, key):
        """Initialize a new AESCipher."""
        self.block_size = 16
        self.cipher = Cipher(algorithms.AES(key), modes.ECB(), default_backend())

    def encrypt(self, raw, use_base64=True):
        """Encrypt data to be sent to device."""
        encryptor = self.cipher.encryptor()
        crypted_text = encryptor.update(self._pad(raw)) + encryptor.finalize()
        return base64.b64encode(crypted_text) if use_base64 else crypted_text

    def decrypt(self, enc, use_base64=True):
        """Decrypt data from device."""
        if use_base64:
            enc = base64.b64decode(enc)

        decryptor = self.cipher.decryptor()
        return self._unpad(decryptor.update(enc) + decryptor.finalize()).decode()

    def _pad(self, data):
        padnum = self.block_size - len(data) % self.block_size
        return data + padnum * chr(padnum).encode()

    @staticmethod
    def _unpad(data):
        return data[: -ord(data[len(data) - 1:])]


class MessageDispatcher(ContextualLogger):
    """Buffer and dispatcher for Tuya messages."""

    # Heartbeats always respond with sequence number 0, so they can't be waited for like
    # other messages. This is a hack to allow waiting for heartbeats.
    HEARTBEAT_SEQNO = -100

    def __init__(self, dev_id, listener):
        """Initialize a new MessageBuffer."""
        super().__init__()
        self.buffer = b""
        self.listeners = {}
        self.listener = listener
        self.set_logger(_LOGGER, dev_id)

    def abort(self):
        """Abort all waiting clients."""
        for key in self.listeners:
            sem = self.listeners[key]
            self.listeners[key] = None

            # TODO: Received data and semahore should be stored separately
            if isinstance(sem, asyncio.Semaphore):
                sem.release()

    async def wait_for(self, seqno, timeout=5):
        """Wait for response to a sequence number to be received and return it."""
        if seqno in self.listeners:
            raise Exception(f"listener exists for {seqno}")

        self.debug("Waiting for sequence number %d", seqno)
        self.listeners[seqno] = asyncio.Semaphore(0)
        try:
            await asyncio.wait_for(self.listeners[seqno].acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            del self.listeners[seqno]
            raise

        return self.listeners.pop(seqno)

    def add_data(self, data):
        """Add new data to the buffer and try to parse messages."""
        self.buffer += data
        header_len = struct.calcsize(MESSAGE_RECV_HEADER_FMT)

        while self.buffer:
            # Check if enough data for message header
            if len(self.buffer) < header_len:
                break

            # Parse header and check if enough data according to length in header
            _, seqno, cmd, length, retcode = struct.unpack_from(
                MESSAGE_RECV_HEADER_FMT, self.buffer
            )
            if len(self.buffer[header_len - 4:]) < length:
                break

            # length includes payload length, retcode, crc and suffix
            if (retcode & 0xFFFFFF00) != 0:
                payload_start = header_len - 4
                payload_length = length - struct.calcsize(MESSAGE_END_FMT)
            else:
                payload_start = header_len
                payload_length = length - 4 - struct.calcsize(MESSAGE_END_FMT)
            payload = self.buffer[payload_start: payload_start + payload_length]

            crc, _ = struct.unpack_from(
                MESSAGE_END_FMT,
                self.buffer[payload_start + payload_length: payload_start + length],
            )

            # CRC calculated from prefix to end of payload
            crc_calc = binascii.crc32(self.buffer[:header_len + payload_length])

            self.buffer = self.buffer[header_len - 4 + length:]

            self._dispatch(TuyaMessage(seqno, cmd, retcode, payload, crc, crc == crc_calc))

    def _dispatch(self, msg):
        """Dispatch a message to someone that is listening."""
        self.debug("Dispatching message %s", msg)
        if msg.seqno in self.listeners:
            self.debug("Dispatching sequence number %d", msg.seqno)
            sem = self.listeners[msg.seqno]
            self.listeners[msg.seqno] = msg
            sem.release()
        elif msg.cmd == COMMAND_HEARTBEAT:
            self.debug("Got heartbeat response")
            if self.HEARTBEAT_SEQNO in self.listeners:
                sem = self.listeners[self.HEARTBEAT_SEQNO]
                self.listeners[self.HEARTBEAT_SEQNO] = msg
                sem.release()
        elif msg.cmd == COMMAND_UPDATE_DPS:
            self.debug("Got normal updatedps response")
        elif msg.cmd == PUSH_STATUS:
            self.debug("Got status update")
            self.listener(msg)
        elif msg.cmd == COMMAND_DP_QUERY_NEW:
            self.debug("Got dp_query_new response")
        elif msg.cmd == COMMAND_CONTROL_NEW:
            self.debug("Got control_new response")
        else:
            self.debug(
                "Got message type %d for unknown listener %d: %s",
                msg.cmd,
                msg.seqno,
                msg,
            )


class TuyaListener(ABC):
    """Listener interface for Tuya device changes."""

    @abstractmethod
    def status_updated(self, status):
        """Device updated status."""

    @abstractmethod
    def disconnected(self):
        """Device disconnected."""


class EmptyListener(TuyaListener):
    """Listener doing nothing."""

    def status_updated(self, status):
        """Device updated status."""

    def disconnected(self):
        """Device disconnected."""


class TuyaProtocol(asyncio.Protocol, ContextualLogger):
    """Implementation of the Tuya protocol."""

    def __init__(self, dev_id, local_key, protocol_version, on_connected, listener, is_gateway):
        """
        Initialize a new TuyaInterface.

        Args:
            dev_id (str): The device id.
            local_key (str): The encryption key.
            protocol_version (float): The protocol version (3.1 or 3.3).
            on_connected (object): Callback when connected.
            listener (object): Listener for events such as status updates.
            is_gateway (bool): Specifies if this is a gateway.
        """
        super().__init__()
        self.loop = asyncio.get_running_loop()
        self.set_logger(_LOGGER, dev_id)
        self.id = dev_id
        self.is_gateway = is_gateway
        self.local_key = local_key.encode("latin1")
        self.version = protocol_version
        self.dev_type = DEV_TYPE_0D if is_gateway else DEV_TYPE_0A
        self.dps_to_request = {"_default": {}}
        self.cipher = AESCipher(self.local_key)
        self.seqno = 0
        self.transport = None
        self.listener = weakref.ref(listener)
        self.dispatcher = self._setup_dispatcher()
        self.on_connected = on_connected
        self.heartbeater = None
        self.dps_cache = {"_default": {}}
        self.sub_devices = []

    def _parse_cid(self, cid):
        if cid:
            if cid not in self.sub_devices:
                raise Exception("Unexpected sub-device cid", cid)
        return cid or '_default'

    def _setup_dispatcher(self):
        """Sets up message dispatcher for this pytuya instance"""
        return MessageDispatcher(self.id, self._status_update)

    def _status_update(self, msg):
        """Handle status updates"""
        decoded_message = self._decode_payload(msg.payload)
        self._update_dps_cache(decoded_message)

        listener = self.listener and self.listener()
        if listener is not None:
            device = decoded_message.get('cid', '_default')
            listener.status_updated({device: self.dps_cache[device]})

    def connection_made(self, transport):
        """Did connect to the device."""

        async def heartbeat_loop():
            """Continuously send heart beat updates."""
            self.debug("Started heartbeat loop")
            while True:
                try:
                    await self.heartbeat()
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                except asyncio.CancelledError:
                    self.debug("Stopped heartbeat loop")
                    raise
                except asyncio.TimeoutError:
                    self.debug("Heartbeat failed due to timeout, disconnecting")
                    break
                except Exception as ex:  # pylint: disable=broad-except
                    self.exception("Heartbeat failed (%s), disconnecting", ex)
                    break

            transport = self.transport
            self.transport = None
            transport.close()

        self.transport = transport
        self.on_connected.set_result(True)
        self.heartbeater = self.loop.create_task(heartbeat_loop())

    def data_received(self, data):
        """Received data from device."""
        self.dispatcher.add_data(data)

    def connection_lost(self, exc):
        """Disconnected from device."""
        self.debug("Connection lost: %s", exc)
        try:
            listener = self.listener and self.listener()
            if listener is not None:
                listener.disconnected()
        except Exception:  # pylint: disable=broad-except
            self.exception("Failed to call disconnected callback")

    async def close(self):
        """Close connection and abort all outstanding listeners."""
        self.debug("Closing connection")
        if self.heartbeater is not None:
            self.heartbeater.cancel()
            try:
                await self.heartbeater
            except asyncio.CancelledError:
                pass
            self.heartbeater = None
        if self.dispatcher is not None:
            self.dispatcher.abort()
            self.dispatcher = None
        if self.transport is not None:
            transport = self.transport
            self.transport = None
            transport.close()

    async def exchange(self, command, dps=None, cid=None):
        """Send and receive a message, returning response from device."""
        self.debug(
            "Sending command %s (device type: %s)",
            command,
            self.dev_type,
        )
        payload = self._generate_payload(command, dps, cid)
        dev_type = self.dev_type

        # Wait for special sequence number if heartbeat
        seqno = (
            MessageDispatcher.HEARTBEAT_SEQNO
            if command == ACTION_HEARTBEAT
            else (self.seqno - 1)
        )

        self.transport.write(payload)
        msg = await self.dispatcher.wait_for(seqno)
        if msg is None:
            self.debug("Wait was aborted for seqno %d", seqno)
            return None

        if not msg.crcpassed:
            self.debug("CRC for sequence number %d failed, resending command %s", seqno, command)
            return await self.exchange(command, dps, cid)

        payload = self._decode_payload(msg.payload)

        # Perform a new exchange (once) if we switched device type
        if dev_type != self.dev_type:
            self.debug(
                "Re-send %s due to device type change (%s -> %s)",
                command,
                dev_type,
                self.dev_type,
            )
            return await self.exchange(command, dps, cid)

        return payload

    async def status(self, cid=None):
        """Return device status."""
        device = self._parse_cid(cid)
        status = await self.exchange(ACTION_STATUS, cid=cid)
        if not status:  # Happens when there's an error in decoding
            return None
        self._update_dps_cache(status)
        return {device: self.dps_cache[device]}

    async def heartbeat(self):
        """Send a heartbeat message."""
        return await self.exchange(ACTION_HEARTBEAT)

    async def update_dps(self, dps=None):
        """
        Request device to update index.

        Args:
            dps([int]): list of dps to update, default=detected&whitelisted
        """
        if self.version == 3.3:
            if dps is None:
                if not self.dps_cache:
                    await self.detect_available_dps()
                if self.dps_cache:
                    dps = [int(dp) for dp in self.dps_cache]
                    # filter non whitelisted dps
                    dps = list(set(dps).intersection(set(UPDATE_DPS_WHITELIST)))
            self.debug("updatedps() entry (dps %s, dps_cache %s)", dps, self.dps_cache)
            payload = self._generate_payload(ACTION_UPDATEDPS, dps)
            self.transport.write(payload)
        return True

    async def set_dp(self, value, dp_index, cid=None):
        """
        Set value (may be any type: bool, int or string) of any dps index.

        Args:
            dp_index(int):   dps index to set
            value: new value for the dps index
            cid: Client ID of sub-device
        """
        self._parse_cid(cid)
        return await self.exchange(ACTION_SET, {str(dp_index): value}, cid)

    async def set_dps(self, dps, cid=None):
        """Set values for a set of datapoints."""
        self._parse_cid(cid)
        return await self.exchange(ACTION_SET, dps, cid)

    async def detect_available_dps(self, cid=None):
        """Return which datapoints are supported by the device."""

        # type_0d devices need a sort of bruteforce querying in order to detect the
        # list of available dps experience shows that the dps available are usually
        # in the ranges [1-25] and [100-110] need to split the bruteforcing in
        # different steps due to request payload limitation (max. length = 255)
        ranges = [(2, 11), (11, 21), (21, 31), (100, 111)]
        device = self._parse_cid(cid)
        self.dps_cache[device] = {}

        for dps_range in ranges:
            # dps 1 must always be sent, otherwise it might fail in case no dps is found
            # in the requested range
            self.dps_to_request[device] = {"1": None}
            self.add_dps_to_request(range(*dps_range), cid)
            try:
                status = await self.status(cid)
                self._update_dps_cache(status)
            except Exception as ex:
                self.exception("Failed to get status for %s: %s", device, ex)
                raise

            self.debug("Detected dps for %s: %s", device, self.dps_cache[device])

        return self.dps_cache[device]

    def add_dps_to_request(self, dp_indicies, cid=None):
        """Add a datapoint (DP) to be included in requests."""
        device = self._parse_cid(cid)
        if isinstance(dp_indicies, int):
            self.dps_to_request[device][str(dp_indicies)] = None
        else:
            self.dps_to_request[device].update({str(index): None for index in dp_indicies})

    def add_sub_device(self, cid):
        """Add a sub-device for a gateway device"""

        if not self.is_gateway:
            raise Exception("Attempt to add sub-device to a non-gateway device")

        self.sub_devices.append(cid)
        self.dps_to_request[cid] = {}
        self.dps_cache[cid] = {}

    def remove_sub_device(self, cid):
        """Removes a sub-device for a gateway device"""
        if not self.is_gateway:
            raise Exception("Attempt to remove sub-device from a non-gateway device")

        self.sub_devices.remove(cid)
        del self.dps_to_request[cid]
        del self.dps_cache[cid]

    def _decode_payload(self, payload):
        """Decodes payload received from a Tuya device"""
        if not payload:
            payload = "{}"
        elif payload.startswith(b"{"):
            pass
        elif payload.startswith(PROTOCOL_VERSION_BYTES_31):
            payload = payload[len(PROTOCOL_VERSION_BYTES_31):]  # remove version header
            # remove (what I'm guessing, but not confirmed is) 16-bytes of MD5
            # hexdigest of payload
            payload = self.cipher.decrypt(payload[16:])
        elif self.version == 3.3:
            if payload.startswith(
                    PROTOCOL_VERSION_BYTES_33
            ):
                payload = payload[len(PROTOCOL_33_HEADER):]
            payload = self.cipher.decrypt(payload, False)

            if "data unvalid" in payload:
                self.dev_type = DEV_TYPE_0D
                self.debug(
                    "switching to dev_type %s",
                    self.dev_type,
                )
                return None
        else:
            raise Exception(f"Unexpected payload={payload}")

        if not isinstance(payload, str):
            payload = payload.decode()
        self.debug("Decrypted payload: %s", payload)
        return json.loads(payload)

    def _generate_payload(self, command, data=None, cid=None):
        """
        Generate the payload to send.

        Args:
            command(str): The type of command.
                This is one of the entries from payload_dict
            data(dict, optional): The data to be send.
                This is what will be passed via the 'dps' entry
            cid(str, optional): The sub-device CID to send
        """

        if cid:
            if command != ACTION_HEARTBEAT:
                if cid not in self.sub_devices:
                    raise Exception("Unexpected sub-device cid", cid)

            payload_dict = GATEWAY_PAYLOAD_DICT
        else:
            payload_dict = PAYLOAD_DICT

        cmd_data = payload_dict[self.dev_type][command]
        json_data = cmd_data["command"]
        command_hb = cmd_data["hexByte"]

        if "gwId" in json_data:
            json_data["gwId"] = self.id
        if "devId" in json_data:
            json_data["devId"] = self.id
        if "uid" in json_data:
            json_data["uid"] = self.id  # still use id, no separate uid
        if "cid" in json_data:
            json_data["cid"] = cid  # for Zigbee gateways, cid specifies the sub-device
        if "t" in json_data:
            json_data["t"] = str(int(time.time()))

        if data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            else:
                json_data["dps"] = data
        elif command_hb == COMMAND_CONTROL_NEW:
            if cid:
                json_data["dps"] = self.dps_to_request[cid]
            else:
                json_data["dps"] = self.dps_to_request['_default']

        payload = json.dumps(json_data).replace(" ", "").encode("utf-8")
        self.debug("Send payload: %s", payload)

        if self.version == 3.3:
            payload = self.cipher.encrypt(payload, False)
            if command_hb not in [
                COMMAND_DP_QUERY,
                COMMAND_DP_QUERY_NEW,
                COMMAND_UPDATE_DPS
            ]:
                # add the 3.3 header
                payload = PROTOCOL_33_HEADER + payload
        elif command == ACTION_SET:
            payload = self.cipher.encrypt(payload)
            to_hash = (
                    b"data="
                    + payload
                    + b"||lpv="
                    + PROTOCOL_VERSION_BYTES_31
                    + b"||"
                    + self.local_key
            )
            hasher = md5()
            hasher.update(to_hash)
            hexdigest = hasher.hexdigest()
            payload = (
                    PROTOCOL_VERSION_BYTES_31
                    + hexdigest[8:][:16].encode("latin1")
                    + payload
            )

        msg = TuyaMessage(self.seqno, command_hb, 0, payload, 0, True)
        self.seqno += 1
        return pack_message(msg)

    def _update_dps_cache(self, status):
        """Updates dps status cache"""
        if not status or "dps" not in status:
            return
        device = status.get("cid", "_default")
        self.dps_cache[device].update(status["dps"])

    def __repr__(self):
        """Return internal string representation of object."""
        return self.id


async def connect(
        address,
        device_id,
        local_key,
        protocol_version,
        listener=None,
        port=6668,
        timeout=5,
        is_gateway=False,
):
    """Connect to a device."""
    loop = asyncio.get_running_loop()
    on_connected = loop.create_future()
    _, protocol = await loop.create_connection(
        lambda: TuyaProtocol(
            device_id,
            local_key,
            protocol_version,
            on_connected,
            listener or EmptyListener(),
            is_gateway,
            ),
        address,
        port,
    )

    await asyncio.wait_for(on_connected, timeout=timeout)
    return protocol
