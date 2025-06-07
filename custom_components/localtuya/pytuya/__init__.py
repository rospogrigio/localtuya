# PyTuya Module
# -*- coding: utf-8 -*-
"""
Python module to interface with Tuya WiFi smart devices.

Author: clach04, postlund
Maintained by: rospogrigio

For more information see https://github.com/clach04/python-tuya

Classes
   TuyaInterface(dev_id, address, local_key=None)
       dev_id (str): Device ID e.g. 01234567891234567890
       address (str): Device Network IP Address e.g. 10.0.1.99
       local_key (str, optional): The encryption key. Defaults to None.

Functions
   json = status()          # returns json payload
   set_version(version)     #  3.1 [default], 3.2, 3.3 or 3.4
   detect_available_dps()   # returns a list of available dps provided by the device
   update_dps(dps)          # sends update dps command
   add_dps_to_request(dp_index)  # adds dp_index to the list of dps used by the
                                  # device (to be queried in the payload)
   set_dp(on, dp_index)   # Set value of any dps index.


 Credits
  * TuyaAPI https://github.com/codetheweb/tuyapi by codetheweb and blackrozes
    For protocol reverse engineering
  * PyTuya https://github.com/clach04/python-tuya by clach04
    The origin of this python module (now abandoned)
  * Tuya Protocol 3.4 Support by uzlonewolf
    Enhancement to TuyaMessage logic for multi-payload messages and Tuya Protocol 3.4 support
  * TinyTuya https://github.com/jasonacox/tinytuya by jasonacox
    Several CLI tools and code for Tuya devices
"""

import asyncio
import base64
import binascii
import hmac
import json
import logging
import struct
import time
import weakref
from abc import ABC, abstractmethod
from collections import namedtuple
from hashlib import md5, sha256

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

version_tuple = (10, 0, 0)
version = version_string = __version__ = "%d.%d.%d" % version_tuple
__author__ = "rospogrigio"

_LOGGER = logging.getLogger(__name__)

# Tuya Packet Format
TuyaHeader = namedtuple("TuyaHeader", "prefix seqno cmd length")
MessagePayload = namedtuple("MessagePayload", "cmd payload")
try:
    TuyaMessage = namedtuple(
        "TuyaMessage", "seqno cmd retcode payload crc crc_good", defaults=(True,)
    )
except Exception:
    TuyaMessage = namedtuple("TuyaMessage", "seqno cmd retcode payload crc crc_good")

# TinyTuya Error Response Codes
ERR_JSON = 900
ERR_CONNECT = 901
ERR_TIMEOUT = 902
ERR_RANGE = 903
ERR_PAYLOAD = 904
ERR_OFFLINE = 905
ERR_STATE = 906
ERR_FUNCTION = 907
ERR_DEVTYPE = 908
ERR_CLOUDKEY = 909
ERR_CLOUDRESP = 910
ERR_CLOUDTOKEN = 911
ERR_PARAMS = 912
ERR_CLOUD = 913

error_codes = {
    ERR_JSON: "Invalid JSON Response from Device",
    ERR_CONNECT: "Network Error: Unable to Connect",
    ERR_TIMEOUT: "Timeout Waiting for Device",
    ERR_RANGE: "Specified Value Out of Range",
    ERR_PAYLOAD: "Unexpected Payload from Device",
    ERR_OFFLINE: "Network Error: Device Unreachable",
    ERR_STATE: "Device in Unknown State",
    ERR_FUNCTION: "Function Not Supported by Device",
    ERR_DEVTYPE: "Device22 Detected: Retry Command",
    ERR_CLOUDKEY: "Missing Tuya Cloud Key and Secret",
    ERR_CLOUDRESP: "Invalid JSON Response from Cloud",
    ERR_CLOUDTOKEN: "Unable to Get Cloud Token",
    ERR_PARAMS: "Missing Function Parameters",
    ERR_CLOUD: "Error Response from Tuya Cloud",
    None: "Unknown Error",
}


class DecodeError(Exception):
    """Specific Exception caused by decoding error."""

    pass


# Tuya Command Types
# Reference:
# https://github.com/tuya/tuya-iotos-embeded-sdk-wifi-ble-bk7231n/blob/master/sdk/include/lan_protocol.h
AP_CONFIG = 0x01  # FRM_TP_CFG_WF      # only used for ap 3.0 network config
ACTIVE = 0x02  # FRM_TP_ACTV (discard) # WORK_MODE_CMD
SESS_KEY_NEG_START = 0x03  # FRM_SECURITY_TYPE3 # negotiate session key
SESS_KEY_NEG_RESP = 0x04  # FRM_SECURITY_TYPE4 # negotiate session key response
SESS_KEY_NEG_FINISH = 0x05  # FRM_SECURITY_TYPE5 # finalize session key negotiation
UNBIND = 0x06  # FRM_TP_UNBIND_DEV  # DATA_QUERT_CMD - issue command
CONTROL = 0x07  # FRM_TP_CMD         # STATE_UPLOAD_CMD
STATUS = 0x08  # FRM_TP_STAT_REPORT # STATE_QUERY_CMD
HEART_BEAT = 0x09  # FRM_TP_HB
DP_QUERY = 0x0A  # 10 # FRM_QUERY_STAT      # UPDATE_START_CMD - get data points
QUERY_WIFI = 0x0B  # 11 # FRM_SSID_QUERY (discard) # UPDATE_TRANS_CMD
TOKEN_BIND = 0x0C  # 12 # FRM_USER_BIND_REQ   # GET_ONLINE_TIME_CMD - system time (GMT)
CONTROL_NEW = 0x0D  # 13 # FRM_TP_NEW_CMD      # FACTORY_MODE_CMD
ENABLE_WIFI = 0x0E  # 14 # FRM_ADD_SUB_DEV_CMD # WIFI_TEST_CMD
WIFI_INFO = 0x0F  # 15 # FRM_CFG_WIFI_INFO
DP_QUERY_NEW = 0x10  # 16 # FRM_QUERY_STAT_NEW
SCENE_EXECUTE = 0x11  # 17 # FRM_SCENE_EXEC
UPDATEDPS = 0x12  # 18 # FRM_LAN_QUERY_DP    # Request refresh of DPS
UDP_NEW = 0x13  # 19 # FR_TYPE_ENCRYPTION
AP_CONFIG_NEW = 0x14  # 20 # FRM_AP_CFG_WF_V40
BOARDCAST_LPV34 = 0x23  # 35 # FR_TYPE_BOARDCAST_LPV34
LAN_EXT_STREAM = 0x40  # 64 # FRM_LAN_EXT_STREAM


PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"
PROTOCOL_VERSION_BYTES_34 = b"3.4"

PROTOCOL_3x_HEADER = 12 * b"\x00"
PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + PROTOCOL_3x_HEADER
PROTOCOL_34_HEADER = PROTOCOL_VERSION_BYTES_34 + PROTOCOL_3x_HEADER
MESSAGE_HEADER_FMT = ">4I"  # 4*uint32: prefix, seqno, cmd, length [, retcode]
MESSAGE_RECV_HEADER_FMT = ">5I"  # 4*uint32: prefix, seqno, cmd, length, retcode
MESSAGE_RETCODE_FMT = ">I"  # retcode for received messages
MESSAGE_END_FMT = ">2I"  # 2*uint32: crc, suffix
MESSAGE_END_FMT_HMAC = ">32sI"  # 32s:hmac, uint32:suffix
PREFIX_VALUE = 0x000055AA
PREFIX_BIN = b"\x00\x00U\xaa"
SUFFIX_VALUE = 0x0000AA55
SUFFIX_BIN = b"\x00\x00\xaaU"
NO_PROTOCOL_HEADER_CMDS = [
    DP_QUERY,
    DP_QUERY_NEW,
    UPDATEDPS,
    HEART_BEAT,
    SESS_KEY_NEG_START,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_FINISH,
]

HEARTBEAT_INTERVAL = 10

# DPS that are known to be safe to use with update_dps (0x12) command
UPDATE_DPS_WHITELIST = [18, 19, 20]  # Socket (Wi-Fi)

# Tuya Device Dictionary - Command and Payload Overrides
# This is intended to match requests.json payload at
# https://github.com/codetheweb/tuyapi :
# 'type_0a' devices require the 0a command for the DP_QUERY request
# 'type_0d' devices require the 0d command for the DP_QUERY request and a list of
#            dps used set to Null in the request payload
# prefix: # Next byte is command byte ("hexByte") some zero padding, then length
# of remaining payload, i.e. command + suffix (unclear if multiple bytes used for
# length, zero padding implies could be more than one byte)

# Any command not defined in payload_dict will be sent as-is with a
#  payload of {"gwId": "", "devId": "", "uid": "", "t": ""}

payload_dict = {
    # Default Device
    "type_0a": {
        AP_CONFIG: {  # [BETA] Set Control Values on Device
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL: {  # Set Control Values on Device
            "command": {"devId": "", "uid": "", "t": ""},
        },
        STATUS: {  # Get Status from Device
            "command": {"gwId": "", "devId": ""},
        },
        HEART_BEAT: {"command": {"gwId": "", "devId": ""}},
        DP_QUERY: {  # Get Data Points from Device
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL_NEW: {"command": {"devId": "", "uid": "", "t": ""}},
        DP_QUERY_NEW: {"command": {"devId": "", "uid": "", "t": ""}},
        UPDATEDPS: {"command": {"dpId": [18, 19, 20]}},
    },
    # Special Case Device "0d" - Some of these devices
    # Require the 0d command as the DP_QUERY status request and the list of
    # dps requested payload
    "type_0d": {
        DP_QUERY: {  # Get Data Points from Device
            "command_override": CONTROL_NEW,  # Uses CONTROL_NEW command for some reason
            "command": {"devId": "", "uid": "", "t": ""},
        },
    },
    "v3.4": {
        CONTROL: {
            "command_override": CONTROL_NEW,  # Uses CONTROL_NEW command
            "command": {"protocol": 5, "t": "int", "data": ""},
        },
        DP_QUERY: {"command_override": DP_QUERY_NEW},
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
        self._enable_debug = False

    def set_logger(self, logger, device_id, enable_debug=False):
        """Set base logger to use."""
        self._enable_debug = enable_debug
        self._logger = TuyaLoggingAdapter(logger, {"device_id": device_id})

    def debug(self, msg, *args):
        """Debug level log."""
        if not self._enable_debug:
            return
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


def pack_message(msg, hmac_key=None):
    """Pack a TuyaMessage into bytes."""
    end_fmt = MESSAGE_END_FMT_HMAC if hmac_key else MESSAGE_END_FMT
    # Create full message excluding CRC and suffix
    buffer = (
        struct.pack(
            MESSAGE_HEADER_FMT,
            PREFIX_VALUE,
            msg.seqno,
            msg.cmd,
            len(msg.payload) + struct.calcsize(end_fmt),
        )
        + msg.payload
    )
    if hmac_key:
        crc = hmac.new(hmac_key, buffer, sha256).digest()
    else:
        crc = binascii.crc32(buffer) & 0xFFFFFFFF
    # Calculate CRC, add it together with suffix
    buffer += struct.pack(end_fmt, crc, SUFFIX_VALUE)
    return buffer


def unpack_message(data, hmac_key=None, header=None, no_retcode=False, logger=None):
    """Unpack bytes into a TuyaMessage."""
    end_fmt = MESSAGE_END_FMT_HMAC if hmac_key else MESSAGE_END_FMT
    # 4-word header plus return code
    header_len = struct.calcsize(MESSAGE_HEADER_FMT)
    retcode_len = 0 if no_retcode else struct.calcsize(MESSAGE_RETCODE_FMT)
    end_len = struct.calcsize(end_fmt)
    headret_len = header_len + retcode_len

    if len(data) < headret_len + end_len:
        logger.debug(
            "unpack_message(): not enough data to unpack header! need %d but only have %d",
            headret_len + end_len,
            len(data),
        )
        raise DecodeError("Not enough data to unpack header")

    if header is None:
        header = parse_header(data)

    if len(data) < header_len + header.length:
        logger.debug(
            "unpack_message(): not enough data to unpack payload! need %d but only have %d",
            header_len + header.length,
            len(data),
        )
        raise DecodeError("Not enough data to unpack payload")

    retcode = (
        0
        if no_retcode
        else struct.unpack(MESSAGE_RETCODE_FMT, data[header_len:headret_len])[0]
    )
    # the retcode is technically part of the payload, but strip it as we do not want it here
    payload = data[header_len + retcode_len : header_len + header.length]
    crc, suffix = struct.unpack(end_fmt, payload[-end_len:])

    if hmac_key:
        have_crc = hmac.new(
            hmac_key, data[: (header_len + header.length) - end_len], sha256
        ).digest()
    else:
        have_crc = (
            binascii.crc32(data[: (header_len + header.length) - end_len]) & 0xFFFFFFFF
        )

    if suffix != SUFFIX_VALUE:
        logger.debug("Suffix prefix wrong! %08X != %08X", suffix, SUFFIX_VALUE)

    if crc != have_crc:
        if hmac_key:
            logger.debug(
                "HMAC checksum wrong! %r != %r",
                binascii.hexlify(have_crc),
                binascii.hexlify(crc),
            )
        else:
            logger.debug("CRC wrong! %08X != %08X", have_crc, crc)

    return TuyaMessage(
        header.seqno, header.cmd, retcode, payload[:-end_len], crc, crc == have_crc
    )


def parse_header(data):
    """Unpack bytes into a TuyaHeader."""
    header_len = struct.calcsize(MESSAGE_HEADER_FMT)

    if len(data) < header_len:
        raise DecodeError("Not enough data to unpack header")

    prefix, seqno, cmd, payload_len = struct.unpack(
        MESSAGE_HEADER_FMT, data[:header_len]
    )

    if prefix != PREFIX_VALUE:
        # self.debug('Header prefix wrong! %08X != %08X', prefix, PREFIX_VALUE)
        raise DecodeError("Header prefix wrong! %08X != %08X" % (prefix, PREFIX_VALUE))

    # sanity check. currently the max payload length is somewhere around 300 bytes
    if payload_len > 1000:
        raise DecodeError(
            "Header claims the packet size is over 1000 bytes! It is most likely corrupt. Claimed size: %d bytes"
            % payload_len
        )

    return TuyaHeader(prefix, seqno, cmd, payload_len)


class AESCipher:
    """Cipher module for Tuya communication."""

    def __init__(self, key):
        """Initialize a new AESCipher."""
        self.block_size = 16
        self.cipher = Cipher(algorithms.AES(key), modes.ECB(), default_backend())

    def encrypt(self, raw, use_base64=True, pad=True):
        """Encrypt data to be sent to device."""
        encryptor = self.cipher.encryptor()
        if pad:
            raw = self._pad(raw)
        crypted_text = encryptor.update(raw) + encryptor.finalize()
        return base64.b64encode(crypted_text) if use_base64 else crypted_text

    def decrypt(self, enc, use_base64=True, decode_text=True):
        """Decrypt data from device."""
        if use_base64:
            enc = base64.b64decode(enc)

        decryptor = self.cipher.decryptor()
        raw = self._unpad(decryptor.update(enc) + decryptor.finalize())
        return raw.decode("utf-8") if decode_text else raw

    def _pad(self, data):
        padnum = self.block_size - len(data) % self.block_size
        return data + padnum * chr(padnum).encode()

    @staticmethod
    def _unpad(data):
        return data[: -ord(data[len(data) - 1 :])]


class MessageDispatcher(ContextualLogger):
    """Buffer and dispatcher for Tuya messages."""

    # Heartbeats on protocols < 3.3 respond with sequence number 0,
    # so they can't be waited for like other messages.
    # This is a hack to allow waiting for heartbeats.
    HEARTBEAT_SEQNO = -100
    RESET_SEQNO = -101
    SESS_KEY_SEQNO = -102

    def __init__(self, dev_id, listener, protocol_version, local_key, enable_debug):
        """Initialize a new MessageBuffer."""
        super().__init__()
        self.buffer = b""
        self.listeners = {}
        self.listener = listener
        self.version = protocol_version
        self.local_key = local_key
        self.set_logger(_LOGGER, dev_id, enable_debug)

    def abort(self):
        """Abort all waiting clients."""
        for key in self.listeners:
            sem = self.listeners[key]
            self.listeners[key] = None

            # TODO: Received data and semahore should be stored separately
            if isinstance(sem, asyncio.Semaphore):
                sem.release()

    async def wait_for(self, seqno, cmd, timeout=5):
        """Wait for response to a sequence number to be received and return it."""
        if seqno in self.listeners:
            raise Exception(f"listener exists for {seqno}")

        self.debug("Command %d waiting for seq. number %d", cmd, seqno)
        self.listeners[seqno] = asyncio.Semaphore(0)
        try:
            await asyncio.wait_for(self.listeners[seqno].acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self.debug(
                "Command %d timed out waiting for sequence number %d", cmd, seqno
            )
            del self.listeners[seqno]
            raise

        return self.listeners.pop(seqno)

    def add_data(self, data):
        """Add new data to the buffer and try to parse messages."""
        self.buffer += data
        header_len = struct.calcsize(MESSAGE_RECV_HEADER_FMT)

        while self.buffer:
            # Check if enough data for measage header
            if len(self.buffer) < header_len:
                break

            header = parse_header(self.buffer)
            hmac_key = self.local_key if self.version == 3.4 else None
            msg = unpack_message(
                self.buffer, header=header, hmac_key=hmac_key, logger=self
            )
            self.buffer = self.buffer[header_len - 4 + header.length :]
            self._dispatch(msg)

    def _dispatch(self, msg):
        """Dispatch a message to someone that is listening."""
        self.debug("Dispatching message CMD %r %s", msg.cmd, msg)
        if msg.seqno in self.listeners:
            # self.debug("Dispatching sequence number %d", msg.seqno)
            sem = self.listeners[msg.seqno]
            if isinstance(sem, asyncio.Semaphore):
                self.listeners[msg.seqno] = msg
                sem.release()
            else:
                self.debug("Got additional message without request - skipping: %s", sem)
        elif msg.cmd == HEART_BEAT:
            self.debug("Got heartbeat response")
            if self.HEARTBEAT_SEQNO in self.listeners:
                sem = self.listeners[self.HEARTBEAT_SEQNO]
                self.listeners[self.HEARTBEAT_SEQNO] = msg
                sem.release()
        elif msg.cmd == UPDATEDPS:
            self.debug("Got normal updatedps response")
            if self.RESET_SEQNO in self.listeners:
                sem = self.listeners[self.RESET_SEQNO]
                self.listeners[self.RESET_SEQNO] = msg
                sem.release()
        elif msg.cmd == SESS_KEY_NEG_RESP:
            self.debug("Got key negotiation response")
            if self.SESS_KEY_SEQNO in self.listeners:
                sem = self.listeners[self.SESS_KEY_SEQNO]
                self.listeners[self.SESS_KEY_SEQNO] = msg
                sem.release()
        elif msg.cmd == STATUS:
            if self.RESET_SEQNO in self.listeners:
                self.debug("Got reset status update")
                sem = self.listeners[self.RESET_SEQNO]
                self.listeners[self.RESET_SEQNO] = msg
                sem.release()
            else:
                self.debug("Got status update")
                self.listener(msg)
        else:
            if msg.cmd == CONTROL_NEW:
                self.debug("Got ACK message for command %d: will ignore it", msg.cmd)
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

    def __init__(
        self, dev_id, local_key, protocol_version, enable_debug, on_connected, listener
    ):
        """
        Initialize a new TuyaInterface.

        Args:
            dev_id (str): The device id.
            address (str): The network address.
            local_key (str, optional): The encryption key. Defaults to None.

        Attributes:
            port (int): The port to connect to.
        """
        super().__init__()
        self.loop = asyncio.get_running_loop()
        self.set_logger(_LOGGER, dev_id, enable_debug)
        self.id = dev_id
        self.local_key = local_key.encode("latin1")
        self.real_local_key = self.local_key
        self.dev_type = "type_0a"
        self.dps_to_request = {}

        if protocol_version:
            self.set_version(float(protocol_version))
        else:
            # make sure we call our set_version() and not a subclass since some of
            # them (such as BulbDevice) make connections when called
            TuyaProtocol.set_version(self, 3.1)

        self.cipher = AESCipher(self.local_key)
        self.seqno = 1
        self.transport = None
        self.listener = weakref.ref(listener)
        self.dispatcher = self._setup_dispatcher(enable_debug)
        self.on_connected = on_connected
        self.heartbeater = None
        self.dps_cache = {}
        self.local_nonce = b"0123456789abcdef"  # not-so-random random key
        self.remote_nonce = b""

    def set_version(self, protocol_version):
        """Set the device version and eventually start available DPs detection."""
        self.version = protocol_version
        self.version_bytes = str(protocol_version).encode("latin1")
        self.version_header = self.version_bytes + PROTOCOL_3x_HEADER
        if protocol_version == 3.2:  # 3.2 behaves like 3.3 with type_0d
            # self.version = 3.3
            self.dev_type = "type_0d"
        elif protocol_version == 3.4:
            self.dev_type = "v3.4"

    def error_json(self, number=None, payload=None):
        """Return error details in JSON."""
        try:
            spayload = json.dumps(payload)
            # spayload = payload.replace('\"','').replace('\'','')
        except Exception:
            spayload = '""'

        vals = (error_codes[number], str(number), spayload)
        self.debug("ERROR %s - %s - payload: %s", *vals)

        return json.loads('{ "Error":"%s", "Err":"%s", "Payload":%s }' % vals)

    def _setup_dispatcher(self, enable_debug):
        def _status_update(msg):
            if msg.seqno > 0:
                self.seqno = msg.seqno + 1
            decoded_message = self._decode_payload(msg.payload)
            if "dps" in decoded_message:
                self.dps_cache.update(decoded_message["dps"])

            listener = self.listener and self.listener()
            if listener is not None:
                listener.status_updated(self.dps_cache)

        return MessageDispatcher(
            self.id, _status_update, self.version, self.local_key, enable_debug
        )

    def connection_made(self, transport):
        """Did connect to the device."""
        self.transport = transport
        self.on_connected.set_result(True)

    def start_heartbeat(self):
        """Start the heartbeat transmissions with the device."""

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

        self.heartbeater = self.loop.create_task(heartbeat_loop())

    def data_received(self, data):
        """Received data from device."""
        # self.debug("received data=%r", binascii.hexlify(data))
        self.dispatcher.add_data(data)

    def connection_lost(self, exc):
        """Disconnected from device."""
        self.debug("Connection lost: %s", exc)
        self.real_local_key = self.local_key
        try:
            listener = self.listener and self.listener()
            if listener is not None:
                listener.disconnected()
        except Exception:  # pylint: disable=broad-except
            self.exception("Failed to call disconnected callback")

    async def close(self):
        """Close connection and abort all outstanding listeners."""
        self.debug("Closing connection")
        self.real_local_key = self.local_key
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

    async def exchange_quick(self, payload, recv_retries):
        """Similar to exchange() but never retries sending and does not decode the response."""
        if not self.transport:
            self.debug(
                "[" + self.id + "] send quick failed, could not get socket: %s", payload
            )
            return None
        enc_payload = (
            self._encode_message(payload)
            if isinstance(payload, MessagePayload)
            else payload
        )
        # self.debug("Quick-dispatching message %s, seqno %s", binascii.hexlify(enc_payload), self.seqno)

        try:
            self.transport.write(enc_payload)
        except Exception:
            # self._check_socket_close(True)
            self.close()
            return None
        while recv_retries:
            try:
                seqno = MessageDispatcher.SESS_KEY_SEQNO
                msg = await self.dispatcher.wait_for(seqno, payload.cmd)
                # for 3.4 devices, we get the starting seqno with the SESS_KEY_NEG_RESP message
                self.seqno = msg.seqno
            except Exception:
                msg = None
            if msg and len(msg.payload) != 0:
                return msg
            recv_retries -= 1
            if recv_retries == 0:
                self.debug(
                    "received null payload (%r) but out of recv retries, giving up", msg
                )
            else:
                self.debug(
                    "received null payload (%r), fetch new one - %s retries remaining",
                    msg,
                    recv_retries,
                )
        return None

    async def exchange(self, command, dps=None):
        """Send and receive a message, returning response from device."""
        if self.version == 3.4 and self.real_local_key == self.local_key:
            self.debug("3.4 device: negotiating a new session key")
            await self._negotiate_session_key()

        self.debug(
            "Sending command %s (device type: %s)",
            command,
            self.dev_type,
        )
        payload = self._generate_payload(command, dps)
        real_cmd = payload.cmd
        dev_type = self.dev_type
        # self.debug("Exchange: payload %r %r", payload.cmd, payload.payload)

        # Wait for special sequence number if heartbeat or reset
        seqno = self.seqno

        if payload.cmd == HEART_BEAT:
            seqno = MessageDispatcher.HEARTBEAT_SEQNO
        elif payload.cmd == UPDATEDPS:
            seqno = MessageDispatcher.RESET_SEQNO

        enc_payload = self._encode_message(payload)
        self.transport.write(enc_payload)
        msg = await self.dispatcher.wait_for(seqno, payload.cmd)
        if msg is None:
            self.debug("Wait was aborted for seqno %d", seqno)
            return None

        # TODO: Verify stuff, e.g. CRC sequence number?
        if real_cmd in [HEART_BEAT, CONTROL, CONTROL_NEW] and len(msg.payload) == 0:
            # device may send messages with empty payload in response
            # to a HEART_BEAT or CONTROL or CONTROL_NEW command: consider them an ACK
            self.debug("ACK received for command %d: ignoring it", real_cmd)
            return None
        payload = self._decode_payload(msg.payload)

        # Perform a new exchange (once) if we switched device type
        if dev_type != self.dev_type:
            self.debug(
                "Re-send %s due to device type change (%s -> %s)",
                command,
                dev_type,
                self.dev_type,
            )
            return await self.exchange(command, dps)
        return payload

    async def status(self):
        """Return device status."""
        status = await self.exchange(DP_QUERY)
        if status and "dps" in status:
            self.dps_cache.update(status["dps"])
        return self.dps_cache

    async def heartbeat(self):
        """Send a heartbeat message."""
        return await self.exchange(HEART_BEAT)

    async def reset(self, dpIds=None):
        """Send a reset message (3.3 only)."""
        if self.version == 3.3:
            self.dev_type = "type_0a"
            self.debug("reset switching to dev_type %s", self.dev_type)
            return await self.exchange(UPDATEDPS, dpIds)

        return True

    async def update_dps(self, dps=None):
        """
        Request device to update index.

        Args:
            dps([int]): list of dps to update, default=detected&whitelisted
        """
        if self.version in [3.2, 3.3, 3.4]:  # 3.2 behaves like 3.3 with type_0d
            if dps is None:
                if not self.dps_cache:
                    await self.detect_available_dps()
                if self.dps_cache:
                    dps = [int(dp) for dp in self.dps_cache]
                    # filter non whitelisted dps
                    dps = list(set(dps).intersection(set(UPDATE_DPS_WHITELIST)))
            self.debug("updatedps() entry (dps %s, dps_cache %s)", dps, self.dps_cache)
            payload = self._generate_payload(UPDATEDPS, dps)
            enc_payload = self._encode_message(payload)
            self.transport.write(enc_payload)
        return True

    async def set_dp(self, value, dp_index):
        """
        Set value (may be any type: bool, int or string) of any dps index.

        Args:
            dp_index(int):   dps index to set
            value: new value for the dps index
        """
        return await self.exchange(CONTROL, {str(dp_index): value})

    async def set_dps(self, dps):
        """Set values for a set of datapoints."""
        return await self.exchange(CONTROL, dps)

    async def detect_available_dps(self):
        """Return which datapoints are supported by the device."""
        # type_0d devices need a sort of bruteforce querying in order to detect the
        # list of available dps experience shows that the dps available are usually
        # in the ranges [1-25] and [100-110] need to split the bruteforcing in
        # different steps due to request payload limitation (max. length = 255)
        self.dps_cache = {}
        ranges = [(2, 11), (11, 21), (21, 31), (100, 111)]

        for dps_range in ranges:
            # dps 1 must always be sent, otherwise it might fail in case no dps is found
            # in the requested range
            self.dps_to_request = {"1": None}
            self.add_dps_to_request(range(*dps_range))
            try:
                data = await self.status()
            except Exception as ex:
                self.exception("Failed to get status: %s", ex)
                raise
            if "dps" in data:
                self.dps_cache.update(data["dps"])

            if self.dev_type == "type_0a":
                return self.dps_cache
        self.debug("Detected dps: %s", self.dps_cache)
        return self.dps_cache

    def add_dps_to_request(self, dp_indicies):
        """Add a datapoint (DP) to be included in requests."""
        if isinstance(dp_indicies, int):
            self.dps_to_request[str(dp_indicies)] = None
        else:
            self.dps_to_request.update({str(index): None for index in dp_indicies})

    def _decode_payload(self, payload):
        cipher = AESCipher(self.local_key)

        if self.version == 3.4:
            # 3.4 devices encrypt the version header in addition to the payload
            try:
                # self.debug("decrypting=%r", payload)
                payload = cipher.decrypt(payload, False, decode_text=False)
            except Exception as ex:
                self.debug(
                    "incomplete payload=%r with len:%d (%s)", payload, len(payload), ex
                )
                return self.error_json(ERR_PAYLOAD)

            # self.debug("decrypted 3.x payload=%r", payload)

        if payload.startswith(PROTOCOL_VERSION_BYTES_31):
            # Received an encrypted payload
            # Remove version header
            payload = payload[len(PROTOCOL_VERSION_BYTES_31) :]
            # Decrypt payload
            # Remove 16-bytes of MD5 hexdigest of payload
            payload = cipher.decrypt(payload[16:])
        elif self.version >= 3.2:  # 3.2 or 3.3 or 3.4
            # Trim header for non-default device type
            if payload.startswith(self.version_bytes):
                payload = payload[len(self.version_header) :]
                # self.debug("removing 3.x=%r", payload)
            elif self.dev_type == "type_0d" and (len(payload) & 0x0F) != 0:
                payload = payload[len(self.version_header) :]
                # self.debug("removing type_0d 3.x header=%r", payload)

            if self.version != 3.4:
                try:
                    # self.debug("decrypting=%r", payload)
                    payload = cipher.decrypt(payload, False)
                except Exception as ex:
                    self.debug(
                        "incomplete payload=%r with len:%d (%s)",
                        payload,
                        len(payload),
                        ex,
                    )
                    return self.error_json(ERR_PAYLOAD)

                # self.debug("decrypted 3.x payload=%r", payload)
                # Try to detect if type_0d found

            if not isinstance(payload, str):
                try:
                    payload = payload.decode()
                except Exception as ex:
                    self.debug("payload was not string type and decoding failed")
                    raise DecodeError("payload was not a string: %s" % ex)
                    # return self.error_json(ERR_JSON, payload)

            if "data unvalid" in payload:
                self.dev_type = "type_0d"
                self.debug(
                    "'data unvalid' error detected: switching to dev_type %r",
                    self.dev_type,
                )
                return None
        elif not payload.startswith(b"{"):
            self.debug("Unexpected payload=%r", payload)
            return self.error_json(ERR_PAYLOAD, payload)

        if not isinstance(payload, str):
            payload = payload.decode()
        self.debug("Deciphered data = %r", payload)
        try:
            json_payload = json.loads(payload)
        except Exception as ex:
            raise DecodeError(
                "could not decrypt data: wrong local_key? (exception: %s)" % ex
            )
            # json_payload = self.error_json(ERR_JSON, payload)

        # v3.4 stuffs it into {"data":{"dps":{"1":true}}, ...}
        if (
            "dps" not in json_payload
            and "data" in json_payload
            and "dps" in json_payload["data"]
        ):
            json_payload["dps"] = json_payload["data"]["dps"]

        return json_payload

    async def _negotiate_session_key(self):
        self.local_key = self.real_local_key

        rkey = await self.exchange_quick(
            MessagePayload(SESS_KEY_NEG_START, self.local_nonce), 2
        )
        if not rkey or not isinstance(rkey, TuyaMessage) or len(rkey.payload) < 48:
            # error
            self.debug("session key negotiation failed on step 1")
            return False

        if rkey.cmd != SESS_KEY_NEG_RESP:
            self.debug(
                "session key negotiation step 2 returned wrong command: %d", rkey.cmd
            )
            return False

        payload = rkey.payload
        try:
            # self.debug("decrypting %r using %r", payload, self.real_local_key)
            cipher = AESCipher(self.real_local_key)
            payload = cipher.decrypt(payload, False, decode_text=False)
        except Exception as ex:
            self.debug(
                "session key step 2 decrypt failed, payload=%r with len:%d (%s)",
                payload,
                len(payload),
                ex,
            )
            return False

        self.debug("decrypted session key negotiation step 2: payload=%r", payload)

        if len(payload) < 48:
            self.debug("session key negotiation step 2 failed, too short response")
            return False

        self.remote_nonce = payload[:16]
        hmac_check = hmac.new(self.local_key, self.local_nonce, sha256).digest()

        if hmac_check != payload[16:48]:
            self.debug(
                "session key negotiation step 2 failed HMAC check! wanted=%r but got=%r",
                binascii.hexlify(hmac_check),
                binascii.hexlify(payload[16:48]),
            )

        # self.debug("session local nonce: %r remote nonce: %r", self.local_nonce, self.remote_nonce)
        rkey_hmac = hmac.new(self.local_key, self.remote_nonce, sha256).digest()
        await self.exchange_quick(MessagePayload(SESS_KEY_NEG_FINISH, rkey_hmac), None)

        self.local_key = bytes(
            [a ^ b for (a, b) in zip(self.local_nonce, self.remote_nonce)]
        )
        # self.debug("Session nonce XOR'd: %r" % self.local_key)

        cipher = AESCipher(self.real_local_key)
        self.local_key = self.dispatcher.local_key = cipher.encrypt(
            self.local_key, False, pad=False
        )
        self.debug("Session key negotiate success! session key: %r", self.local_key)
        return True

    # adds protocol header (if needed) and encrypts
    def _encode_message(self, msg):
        hmac_key = None
        payload = msg.payload
        self.cipher = AESCipher(self.local_key)
        if self.version == 3.4:
            hmac_key = self.local_key
            if msg.cmd not in NO_PROTOCOL_HEADER_CMDS:
                # add the 3.x header
                payload = self.version_header + payload
            self.debug("final payload for cmd %r: %r", msg.cmd, payload)
            payload = self.cipher.encrypt(payload, False)
        elif self.version >= 3.2:
            # expect to connect and then disconnect to set new
            payload = self.cipher.encrypt(payload, False)
            if msg.cmd not in NO_PROTOCOL_HEADER_CMDS:
                # add the 3.x header
                payload = self.version_header + payload
        elif msg.cmd == CONTROL:
            # need to encrypt
            payload = self.cipher.encrypt(payload)
            preMd5String = (
                b"data="
                + payload
                + b"||lpv="
                + PROTOCOL_VERSION_BYTES_31
                + b"||"
                + self.local_key
            )
            m = md5()
            m.update(preMd5String)
            hexdigest = m.hexdigest()
            # some tuya libraries strip 8: to :24
            payload = (
                PROTOCOL_VERSION_BYTES_31
                + hexdigest[8:][:16].encode("latin1")
                + payload
            )

        self.cipher = None
        msg = TuyaMessage(self.seqno, msg.cmd, 0, payload, 0, True)
        self.seqno += 1  # increase message sequence number
        buffer = pack_message(msg, hmac_key=hmac_key)
        # self.debug("payload encrypted with key %r => %r", self.local_key, binascii.hexlify(buffer))
        return buffer

    def _generate_payload(self, command, data=None, gwId=None, devId=None, uid=None):
        """
        Generate the payload to send.

        Args:
            command(str): The type of command.
                This is one of the entries from payload_dict
            data(dict, optional): The data to be send.
                This is what will be passed via the 'dps' entry
            gwId(str, optional): Will be used for gwId
            devId(str, optional): Will be used for devId
            uid(str, optional): Will be used for uid
        """
        json_data = command_override = None

        if command in payload_dict[self.dev_type]:
            if "command" in payload_dict[self.dev_type][command]:
                json_data = payload_dict[self.dev_type][command]["command"]
            if "command_override" in payload_dict[self.dev_type][command]:
                command_override = payload_dict[self.dev_type][command][
                    "command_override"
                ]

        if self.dev_type != "type_0a":
            if (
                json_data is None
                and command in payload_dict["type_0a"]
                and "command" in payload_dict["type_0a"][command]
            ):
                json_data = payload_dict["type_0a"][command]["command"]
            if (
                command_override is None
                and command in payload_dict["type_0a"]
                and "command_override" in payload_dict["type_0a"][command]
            ):
                command_override = payload_dict["type_0a"][command]["command_override"]

        if command_override is None:
            command_override = command
        if json_data is None:
            # I have yet to see a device complain about included but unneeded attribs, but they *will*
            # complain about missing attribs, so just include them all unless otherwise specified
            json_data = {"gwId": "", "devId": "", "uid": "", "t": ""}

        if "gwId" in json_data:
            if gwId is not None:
                json_data["gwId"] = gwId
            else:
                json_data["gwId"] = self.id
        if "devId" in json_data:
            if devId is not None:
                json_data["devId"] = devId
            else:
                json_data["devId"] = self.id
        if "uid" in json_data:
            if uid is not None:
                json_data["uid"] = uid
            else:
                json_data["uid"] = self.id
        if "t" in json_data:
            if json_data["t"] == "int":
                json_data["t"] = int(time.time())
            else:
                json_data["t"] = str(int(time.time()))

        if data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            elif "data" in json_data:
                json_data["data"] = {"dps": data}
            else:
                json_data["dps"] = data
        elif self.dev_type == "type_0d" and command == DP_QUERY:
            json_data["dps"] = self.dps_to_request

        if json_data == "":
            payload = ""
        else:
            payload = json.dumps(json_data)
        # if spaces are not removed device does not respond!
        payload = payload.replace(" ", "").encode("utf-8")
        self.debug("Sending payload: %s", payload)

        return MessagePayload(command_override, payload)

    def __repr__(self):
        """Return internal string representation of object."""
        return self.id


async def connect(
    address,
    device_id,
    local_key,
    protocol_version,
    enable_debug,
    listener=None,
    port=6668,
    timeout=5,
):
    """Connect to a device."""
    loop = asyncio.get_running_loop()
    on_connected = loop.create_future()
    _, protocol = await loop.create_connection(
        lambda: TuyaProtocol(
            device_id,
            local_key,
            protocol_version,
            enable_debug,
            on_connected,
            listener or EmptyListener(),
        ),
        address,
        port,
    )

    await asyncio.wait_for(on_connected, timeout=timeout)
    return protocol
