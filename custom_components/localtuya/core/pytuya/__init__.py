# PyTuya Module
# -*- coding: utf-8 -*-
"""
Python module to interface with Tuya WiFi smart devices.

Author: clach04, postlund
Maintained by: rospogrigio, xZetsubou

For more information see https://github.com/clach04/python-tuya

Classes
    TuyaInterface(dev_id, address, local_key=None)
        dev_id (str): Device ID e.g. 01234567891234567890
        address (str): Device Network IP Address e.g. 10.0.1.99
        local_key (str, optional): The encryption key. Defaults to None.

Functions
    json = status()          # returns json payload
    set_version(version)     #  3.1 [default], 3.2, 3.3, 3.4 or 3.5
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
  * Tuya Protocol 3.4 and 3.5 Support by uzlonewolf
    Enhancement to TuyaMessage logic for multi-payload messages and Tuya Protocol 3.4 support
  * TinyTuya https://github.com/jasonacox/tinytuya by jasonacox, uzlonewolf
    Several CLI tools and code for Tuya devices
"""

import os
import asyncio
import errno
import base64
import binascii
import hmac
import json
import logging
import struct
import time
import weakref
from enum import Enum
from abc import ABC, abstractmethod
from typing import Self
from collections import namedtuple
from hashlib import md5, sha256

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

version_tuple = (2024, 6, 0)
version = version_string = __version__ = "%d.%d.%d" % version_tuple
__author__ = "rospogrigio, xZetsubou"

_LOGGER = logging.getLogger(__name__)

# Tuya Packet Format
TuyaHeader = namedtuple("TuyaHeader", "prefix seqno cmd length total_length")
MessagePayload = namedtuple("MessagePayload", "cmd payload")
try:
    TuyaMessage = namedtuple(
        "TuyaMessage",
        "seqno cmd retcode payload crc crc_good prefix iv",
        defaults=(True, 0x55AA, None),
    )
except:
    TuyaMessage = namedtuple(
        "TuyaMessage", "seqno cmd retcode payload crc crc_good prefix iv"
    )

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


class SubdeviceState(Enum):
    ONLINE = 1
    OFFLINE = 2
    ABSENT = 3


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

UPDATE_DPS_LIST = [3.2, 3.3, 3.4, 3.5]  # 3.2 behaves like 3.3 with type_0d

PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"
PROTOCOL_VERSION_BYTES_34 = b"3.4"
PROTOCOL_VERSION_BYTES_35 = b"3.5"

PROTOCOL_3x_HEADER = 12 * b"\x00"
PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + PROTOCOL_3x_HEADER
PROTOCOL_34_HEADER = PROTOCOL_VERSION_BYTES_34 + PROTOCOL_3x_HEADER
PROTOCOL_35_HEADER = PROTOCOL_VERSION_BYTES_35 + PROTOCOL_3x_HEADER
MESSAGE_RECV_HEADER_FMT = ">5I"  # 4*uint32: prefix, seqno, cmd, length, retcode
MESSAGE_HEADER_FMT = MESSAGE_HEADER_FMT_55AA = (
    ">4I"  # 4*uint32: prefix, seqno, cmd, length [, retcode]
)
MESSAGE_HEADER_FMT_6699 = ">IHIII"  # 4*uint32: prefix, unknown, seqno, cmd, length
MESSAGE_RETCODE_FMT = ">I"  # retcode for received messages
MESSAGE_END_FMT = MESSAGE_END_FMT_55AA = ">2I"  # 2*uint32: crc, suffix
MESSAGE_END_FMT_HMAC = ">32sI"  # 32s:hmac, uint32:suffix
MESSAGE_END_FMT_6699 = ">16sI"  # 16s:tag, suffix
PREFIX_VALUE = PREFIX_55AA_VALUE = 0x000055AA
PREFIX_BIN = PREFIX_55AA_BIN = b"\x00\x00U\xaa"
SUFFIX_VALUE = SUFFIX_55AA_VALUE = 0x0000AA55
SUFFIX_BIN = SUFFIX_55AA_BIN = b"\x00\x00\xaaU"
PREFIX_6699_VALUE = 0x00006699
PREFIX_6699_BIN = b"\x00\x00\x66\x99"
SUFFIX_6699_VALUE = 0x00009966
SUFFIX_6699_BIN = b"\x00\x00\x99\x66"

NO_PROTOCOL_HEADER_CMDS = [
    DP_QUERY,
    DP_QUERY_NEW,
    UPDATEDPS,
    HEART_BEAT,
    SESS_KEY_NEG_START,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_FINISH,
    LAN_EXT_STREAM,
]

HEARTBEAT_INTERVAL = 9

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
            "command": {"gwId": "", "devId": "", "uid": "", "t": "", "cid": ""},
        },
        CONTROL: {  # Set Control Values on Device
            "command": {"devId": "", "uid": "", "t": "", "cid": ""},
        },
        STATUS: {  # Get Status from Device
            "command": {"gwId": "", "devId": "", "cid": ""},
        },
        HEART_BEAT: {"command": {"gwId": "", "devId": ""}},
        DP_QUERY: {  # Get Data Points from Device
            "command": {"gwId": "", "devId": "", "uid": "", "t": "", "cid": ""},
        },
        CONTROL_NEW: {"command": {"devId": "", "uid": "", "t": "", "cid": ""}},
        DP_QUERY_NEW: {"command": {"devId": "", "uid": "", "t": "", "cid": ""}},
        UPDATEDPS: {"command": {"dpId": [18, 19, 20], "cid": ""}},
        LAN_EXT_STREAM: {"command": {"reqType": "", "data": {}}},
    },
    # Special Case Device "0d" - Some of these devices
    # Require the 0d command as the DP_QUERY status request and the list of
    # dps requested payload
    "type_0d": {
        DP_QUERY: {  # Get Data Points from Device
            "command_override": CONTROL_NEW,  # Uses CONTROL_NEW command for some reason
            "command": {"devId": "", "uid": "", "t": "", "cid": ""},
        },
    },
    "v3.4": {
        CONTROL: {
            "command_override": CONTROL_NEW,  # Uses CONTROL_NEW command
            "command": {"protocol": 5, "t": "int", "data": {"cid": ""}},
        },
        DP_QUERY: {"command_override": DP_QUERY_NEW},
    },
    "v3.5": {
        CONTROL: {
            "command_override": CONTROL_NEW,  # Uses CONTROL_NEW command
            "command": {"protocol": 5, "t": "int", "data": {"cid": ""}},
        },
        DP_QUERY: {"command_override": DP_QUERY_NEW},
    },
}


class TuyaLoggingAdapter(logging.LoggerAdapter):
    """Adapter that adds device id to all log points."""

    def process(self, msg, kwargs):
        """Process log point and return output."""
        dev_id = self.extra["device_id"]
        name = self.extra.get("name")
        prefix = f"{dev_id[0:3]}...{dev_id[-3:]}"
        if name:
            return f"[{prefix} - {name}] {msg}", kwargs

        return f"[{prefix}] {msg}", kwargs


class ContextualLogger:
    """Contextual logger adding device id to log points."""

    def __init__(self):
        """Initialize a new ContextualLogger."""
        self._logger = None
        self._enable_debug = False

        self._reset_warning = int(time.time())
        self._last_warning = ""

    def set_logger(self, logger, device_id, enable_debug=False, name=None):
        """Set base logger to use."""
        self._enable_debug = enable_debug
        self._logger = TuyaLoggingAdapter(
            logger, {"device_id": device_id, "name": name}
        )
        return self

    def debug(self, msg, *args, force=False):
        """Debug level log for device. force will ignore device debug check."""
        if not self._enable_debug and not force:
            return
        return self._logger.log(logging.DEBUG, msg, *args)

    def info(self, msg, *args, clear_warning=False):
        """Info level log. clear_warning to re-enable warings msgs if duplicated"""
        if clear_warning:
            self._last_warning = ""

        return self._logger.log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """Warning method log."""
        if msg != self._last_warning:
            self._last_warning = msg
            return self._logger.log(logging.WARNING, msg, *args)
        # else:
        #     self.info(msg)

    def error(self, msg, *args):
        """Error level log."""
        return self._logger.log(logging.ERROR, msg, *args)

    def exception(self, msg, *args):
        """Exception level log."""
        return self._logger.exception(msg, *args)


def pack_message(msg, hmac_key=None):
    """Pack a TuyaMessage into bytes."""
    if msg.prefix == PREFIX_55AA_VALUE:
        header_fmt = MESSAGE_HEADER_FMT_55AA
        end_fmt = MESSAGE_END_FMT_HMAC if hmac_key else MESSAGE_END_FMT_55AA
        msg_len = len(msg.payload) + struct.calcsize(end_fmt)
        header_data = (msg.prefix, msg.seqno, msg.cmd, msg_len)
    elif msg.prefix == PREFIX_6699_VALUE:
        if not hmac_key:
            raise TypeError("key must be provided to pack 6699-format messages")
        header_fmt = MESSAGE_HEADER_FMT_6699
        end_fmt = MESSAGE_END_FMT_6699
        msg_len = len(msg.payload) + (struct.calcsize(end_fmt) - 4) + 12
        if type(msg.retcode) == int:
            msg_len += struct.calcsize(MESSAGE_RETCODE_FMT)
        header_data = (msg.prefix, 0, msg.seqno, msg.cmd, msg_len)
    else:
        raise ValueError(
            "pack_message() cannot handle message format %08X" % msg.prefix
        )

    # Create full message excluding CRC and suffix
    data = struct.pack(header_fmt, *header_data)

    if msg.prefix == PREFIX_6699_VALUE:
        cipher = AESCipher(hmac_key)
        if type(msg.retcode) == int:
            raw = struct.pack(MESSAGE_RETCODE_FMT, msg.retcode) + msg.payload
        else:
            raw = msg.payload
        data2 = cipher.encrypt(
            raw,
            use_base64=False,
            pad=False,
            iv=True if not msg.iv else msg.iv,
            header=data[4:],
        )
        data += data2 + SUFFIX_6699_BIN
    else:
        data += msg.payload
        if hmac_key:
            crc = hmac.new(hmac_key, data, sha256).digest()
        else:
            crc = binascii.crc32(data) & 0xFFFFFFFF
        # Calculate CRC, add it together with suffix
        data += struct.pack(end_fmt, crc, SUFFIX_VALUE)

    return data


def unpack_message(data, hmac_key=None, header=None, no_retcode=False, logger=_LOGGER):
    """Unpack bytes into a TuyaMessage."""
    if header is None:
        header = parse_header(data)

    if header.prefix == PREFIX_55AA_VALUE:
        # 4-word header plus return code
        header_len = struct.calcsize(MESSAGE_HEADER_FMT_55AA)
        end_fmt = MESSAGE_END_FMT_HMAC if hmac_key else MESSAGE_END_FMT_55AA
        retcode_len = 0 if no_retcode else struct.calcsize(MESSAGE_RETCODE_FMT)
        msg_len = header_len + header.length
    elif header.prefix == PREFIX_6699_VALUE:
        if not hmac_key:
            raise TypeError("key must be provided to unpack 6699-format messages")
        header_len = struct.calcsize(MESSAGE_HEADER_FMT_6699)
        end_fmt = MESSAGE_END_FMT_6699
        retcode_len = 0
        msg_len = header_len + header.length + 4
    else:
        raise ValueError(
            "unpack_message() cannot handle message format %08X" % header.prefix
        )

    if len(data) < msg_len:
        logger.debug(
            "unpack_message(): not enough data to unpack payload! need %d but only have %d",
            header_len + header.length,
            len(data),
        )
        raise DecodeError(f"Not enough data to unpack payload: {data}")

    end_len = struct.calcsize(end_fmt)
    # the retcode is technically part of the payload, but strip it as we do not want it here
    retcode = (
        0
        if not retcode_len
        else struct.unpack(
            MESSAGE_RETCODE_FMT, data[header_len : header_len + retcode_len]
        )[0]
    )
    payload = data[header_len + retcode_len : msg_len]
    crc, suffix = struct.unpack(end_fmt, payload[-end_len:])
    payload = payload[:-end_len]

    if header.prefix == PREFIX_55AA_VALUE:
        if hmac_key:
            have_crc = hmac.new(
                hmac_key, data[: (header_len + header.length) - end_len], sha256
            ).digest()
        else:
            have_crc = (
                binascii.crc32(data[: (header_len + header.length) - end_len])
                & 0xFFFFFFFF
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
        crc_good = crc == have_crc
        iv = None
    elif header.prefix == PREFIX_6699_VALUE:
        iv = payload[:12]
        payload = payload[12:]
        try:
            cipher = AESCipher(hmac_key)
            payload = cipher.decrypt(
                payload,
                use_base64=False,
                decode_text=False,
                iv=iv,
                header=data[4:header_len],
                tag=crc,
            )
            crc_good = True
        except:
            crc_good = False

        retcode_len = struct.calcsize(MESSAGE_RETCODE_FMT)
        if no_retcode is False:
            pass
        elif (
            no_retcode is None
            and payload[0:1] != b"{"
            and payload[retcode_len : retcode_len + 1] == b"{"
        ):
            retcode_len = struct.calcsize(MESSAGE_RETCODE_FMT)
        else:
            retcode_len = 0
        if retcode_len:
            retcode = struct.unpack(MESSAGE_RETCODE_FMT, payload[:retcode_len])[0]
            payload = payload[retcode_len:]

    return TuyaMessage(
        header.seqno, header.cmd, retcode, payload, crc, crc_good, header.prefix, iv
    )


def parse_header(data, logger=_LOGGER):
    """Unpack bytes into a TuyaHeader."""
    if data[:4] == PREFIX_6699_BIN:
        fmt = MESSAGE_HEADER_FMT_6699
    else:
        fmt = MESSAGE_HEADER_FMT_55AA

    header_len = struct.calcsize(fmt)

    if len(data) < header_len:
        err = "Not enough data to unpack header"
        logger.error(err)
        raise DecodeError(err)

    unpacked = struct.unpack(fmt, data[:header_len])
    prefix = unpacked[0]

    if prefix == PREFIX_55AA_VALUE:
        prefix, seqno, cmd, payload_len = unpacked
        total_length = payload_len + header_len
    elif prefix == PREFIX_6699_VALUE:
        prefix, unknown, seqno, cmd, payload_len = unpacked
        # seqno |= unknown << 32
        total_length = payload_len + header_len + len(SUFFIX_6699_BIN)
    else:
        err = f"Header prefix wrong! {prefix} is not {PREFIX_55AA_VALUE} or {PREFIX_6699_VALUE}"
        logger.error(err)
        raise DecodeError(err)

    # sanity check. currently the max payload length is somewhere around 300 bytes
    if payload_len > 2000:
        err = f"Header claims the packet size is over 2000 bytes!  It is most likely corrupt. Claimed size: {payload_len} bytes. fmt: {fmt} unpacked: {unpacked}"
        logger.error(err)
        raise DecodeError(err)

    return TuyaHeader(prefix, seqno, cmd, payload_len, total_length)


class AESCipher:
    """Cipher module for Tuya communication."""

    def __init__(self, key):
        """Initialize a new AESCipher."""
        self.block_size = 16
        self.key = key
        self.cipher = Cipher(algorithms.AES(key), modes.ECB(), default_backend())

    def encrypt(self, raw, use_base64=True, pad=True, iv=False, header=None):
        """Encrypt data to be sent to device."""
        if iv:
            if iv is True:
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    iv = b"0123456789ab"
                else:
                    iv = str(time.time() * 10)[:12].encode("utf8")
            encryptor = Cipher(algorithms.AES(self.key), modes.GCM(iv)).encryptor()
            if header:
                encryptor.authenticate_additional_data(header)
            crypted_text = encryptor.update(raw) + encryptor.finalize()
            crypted_text = iv + crypted_text + encryptor.tag
        else:
            encryptor = self.cipher.encryptor()
            if pad:
                raw = self._pad(raw)
            crypted_text = encryptor.update(raw) + encryptor.finalize()
        return base64.b64encode(crypted_text) if use_base64 else crypted_text

    def decrypt(
        self, enc, use_base64=True, decode_text=True, iv=False, header=None, tag=None
    ):
        """Decrypt data from device."""
        if not iv:
            if use_base64:
                enc = base64.b64decode(enc)

        if iv:
            if iv is True:
                iv = enc[:12]
                enc = enc[12:]
            if tag is None:
                decryptor = Cipher(
                    algorithms.AES(self.key), modes.CTR(iv + b"\x00\x00\x00\x02")
                ).decryptor()
            else:
                decryptor = Cipher(
                    algorithms.AES(self.key), modes.GCM(iv, tag)
                ).decryptor()
            if header and (tag is not None):
                decryptor.authenticate_additional_data(header)
            raw = decryptor.update(enc) + decryptor.finalize()
        else:
            decryptor = self.cipher.decryptor()
            raw = decryptor.update(enc) + decryptor.finalize()
            raw = self._unpad(raw)

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
    SUB_DEVICE_QUERY_SEQNO = -103

    def __init__(self, dev_id, callback_status_update, protocol_version, local_key):
        """Initialize a new MessageBuffer."""
        super().__init__()
        self.buffer = b""
        self.listeners: dict[str, asyncio.Semaphore] = {}
        self.callback_status_update = callback_status_update
        self.version = protocol_version
        self.local_key = local_key

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
            self.debug(f"listener exists for {seqno}")
            if seqno == self.HEARTBEAT_SEQNO:
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
            raise TimeoutError(
                f"Command {cmd} timed out waiting for sequence number {seqno}"
            )
        return self.listeners.pop(seqno)

    def add_data(self, data):
        """Add new data to the buffer and try to parse messages."""
        self.buffer += data

        header_len = struct.calcsize(MESSAGE_RECV_HEADER_FMT)
        while self.buffer:
            # Check if enough data for measage header
            if len(self.buffer) < header_len:
                break

            prefix_offset_55AA = self.buffer.find(PREFIX_55AA_BIN)
            prefix_offset_6699 = self.buffer.find(PREFIX_6699_BIN)
            prefixes = (prefix_offset_55AA, prefix_offset_6699)

            # If somehow we got unexpected message, we will ignore it and reset the buffer.
            if prefix_offset_55AA < 0 and prefix_offset_6699 < 0:
                self.debug(f"Got unexpected Message prefix: {self.buffer}", force=True)
                self.buffer = b""
                break

            # If the prefix is not at the start of the message.
            if prefix_offset_55AA != 0 and prefix_offset_6699 != 0:
                self.debug(f"Message prefix offset not at the start {self.buffer}")
                prefix_offset = min(prefix for prefix in prefixes if not prefix < 0)
                self.buffer = self.buffer[prefix_offset:]

            header = parse_header(self.buffer, logger=self)
            # Check if the all data for the message has been received.
            if len(self.buffer) < header.total_length:
                break

            hmac_key = self.local_key if self.version >= 3.4 else None
            no_retcode = False
            msg = unpack_message(
                self.buffer,
                header=header,
                hmac_key=hmac_key,
                no_retcode=no_retcode,
                logger=self,
            )
            self.buffer = self.buffer[header.total_length :]
            self._dispatch(msg)

    def _dispatch(self, msg):
        """Dispatch a message to someone that is listening."""

        self.debug("Dispatching message CMD %r %s", msg.cmd, msg)

        if msg.seqno in self.listeners:
            self.debug("Dispatching sequence number %d", msg.seqno)
            self._release_listener(msg.seqno, msg)

        if msg.cmd == HEART_BEAT:
            self.debug("Got heartbeat response")
            self._release_listener(self.HEARTBEAT_SEQNO, msg)
        elif msg.cmd == UPDATEDPS:
            self.debug("Got normal updatedps response")
            self._release_listener(self.RESET_SEQNO, msg)
        elif msg.cmd == SESS_KEY_NEG_RESP:
            self.debug("Got key negotiation response")
            self._release_listener(self.SESS_KEY_SEQNO, msg)
        elif msg.cmd == STATUS:
            if self.RESET_SEQNO in self.listeners:
                self.debug("Got reset status update")
                self._release_listener(self.RESET_SEQNO, msg)
            else:
                self.debug("Got status update")
                self.callback_status_update(msg)
        elif msg.cmd == LAN_EXT_STREAM:
            self._release_listener(self.SUB_DEVICE_QUERY_SEQNO, msg)
            if msg.payload:
                self.debug(f"Got Sub-devices status update")
                self.callback_status_update(msg)
        else:
            if msg.cmd == CONTROL_NEW or not msg.payload:
                self.debug(
                    "Got ACK message for command %d: ignoring it %s", msg.cmd, msg.seqno
                )
                self.callback_status_update(msg, ack=True)
            elif msg.seqno not in self.listeners:
                self.debug(
                    "Got message type %d for unknown listener %d: %s",
                    msg.cmd,
                    msg.seqno,
                    msg,
                )

    def _release_listener(self, seqno, msg):
        if seqno not in self.listeners:
            return

        sem = self.listeners[seqno]
        if isinstance(sem, asyncio.Semaphore):
            self.listeners[seqno] = msg
            sem.release()
        else:
            self.debug(f"{seqno} - Got additional message without request: skip {sem}")


class TuyaListener(ABC):
    """Listener interface for Tuya device changes."""

    sub_devices: dict[str, Self]

    @abstractmethod
    def status_updated(self, status):
        """Device updated status."""

    @abstractmethod
    def disconnected(self, exc=""):
        """Device disconnected."""

    @abstractmethod
    def subdevice_state_updated(self, state: SubdeviceState):
        """Device is offline or online."""


class EmptyListener(TuyaListener):
    """Listener doing nothing."""

    def status_updated(self, status):
        """Device updated status."""

    def disconnected(self, exc=""):
        """Device disconnected."""

    def subdevice_state_updated(self, state: SubdeviceState):
        """Device is offline or online."""


class TuyaProtocol(asyncio.Protocol, ContextualLogger):
    """Implementation of the Tuya protocol."""

    def __init__(
        self,
        dev_id: str,
        local_key: str,
        protocol_version: float,
        enable_debug: bool,
        on_connected: asyncio.Future,
        listener: TuyaListener,
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
        self.dispatcher = self._setup_dispatcher()
        self.on_connected = on_connected
        self.heartbeater: asyncio.Task | None = None
        self._sub_devs_query_task: asyncio.Task | None = None
        self.dps_cache = {}
        self.sub_devices_states = {"online": [], "offline": []}
        self.local_nonce = b"0123456789abcdef"  # not-so-random random key
        self.remote_nonce = b""
        self.dps_whitelist = UPDATE_DPS_WHITELIST
        self.dispatched_dps = {}  # Store payload so we can trigger an event in HA.
        self._last_command_sent = 1
        self.enable_debug(enable_debug)

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
        elif protocol_version == 3.5:
            self.dev_type = "v3.5"

    def error_json(self, number=None, payload=None):
        """Return error details in JSON."""
        try:
            spayload = json.dumps(payload)
            # spayload = payload.replace('\"','').replace('\'','')
        except Exception:  # pylint: disable=broad-except
            spayload = '""'

        vals = (error_codes[number], str(number), spayload)
        self.debug("ERROR %s - %s - payload: %s", *vals)

        return json.loads('{ "Error":"%s", "Err":"%s", "Payload":%s }' % vals)

    def _msg_subdevs_query(self, decoded_message):
        """
        Handle the sub-devices query message.
        Message: {"online": [cids, ...], "offline": [cids, ...], "nearby": [cids, ...]}
        """

        async def _action():
            try:
                await asyncio.sleep(2)

                self.debug(f"Sub-Devices States Update: {self.sub_devices_states}")
                on_devs = self.sub_devices_states.get("online")
                off_devs = self.sub_devices_states.get("offline")
                listener = self.listener and self.listener()
                if listener is None or (on_devs is None and off_devs is None):
                    return
                for cid, device in listener.sub_devices.items():
                    if cid in on_devs:
                        device.subdevice_state(SubdeviceState.ONLINE)
                    elif cid in off_devs:
                        device.subdevice_state(SubdeviceState.OFFLINE)
                    else:
                        device.subdevice_state(SubdeviceState.ABSENT)
            except asyncio.CancelledError:
                pass

        if (data := decoded_message.get("data")) and isinstance(data, dict):
            devs_states = self.sub_devices_states
            updated_states = {}

            cached_on_devs = devs_states.get("online", [])
            cached_off_devs = devs_states.get("offline", [])

            on_devs, off_devs = data.get("online", []), data.get("offline", [])

            updated_states["online"] = list(set(cached_on_devs + on_devs))
            updated_states["offline"] = list(set(cached_off_devs + off_devs))

            if self._sub_devs_query_task is not None:
                self._sub_devs_query_task.cancel()

            self.sub_devices_states = updated_states
            self._sub_devs_query_task = self.loop.create_task(_action())

    def _setup_dispatcher(self) -> MessageDispatcher:
        def _status_update(msg, ack=False):
            if msg.seqno > 0:
                if msg.seqno >= self.seqno:
                    self.seqno = msg.seqno + 1
                if ack:
                    self.debug(
                        f"Got update ack message update seqno only. msg.seqno={msg.seqno} self.seqno={self.seqno}"
                    )
                    return

            decoded_message: dict = self._decode_payload(msg.payload)
            cid = None

            # Sub-devices query message.
            if msg.cmd == LAN_EXT_STREAM:
                return self._msg_subdevs_query(decoded_message)

            if "dps" not in decoded_message:
                return

            if dps_payload := decoded_message.get("dps"):
                if cid := decoded_message.get("cid"):
                    self.dps_cache.setdefault(cid, {})
                    self.dps_cache[cid].update(dps_payload)
                else:
                    self.dps_cache.setdefault("parent", {})
                    self.dps_cache["parent"].update(dps_payload)

            listener = self.listener and self.listener()
            if listener is not None:
                if cid:
                    # Don't pass sub-device's payload to the (fake)gateway!
                    if not (listener := listener.sub_devices.get(cid, None)):
                        return self.debug(
                            f'Payload for missing sub-device discarded: "{decoded_message}"'
                        )
                    status = self.dps_cache.get(cid, {})
                else:
                    status = self.dps_cache.get("parent", {})

                listener.status_updated(status)

        return MessageDispatcher(self.id, _status_update, self.version, self.local_key)

    def connection_made(self, transport):
        """Did connect to the device."""
        self.transport = transport
        self.on_connected.set_result(True)

    def keep_alive(self, is_gateway: bool = False):
        """
        Start the heartbeat transmissions with the device.
            is_gateway: will use subdevices_query as heartbeat.
        """

        async def keep_alive_loop(action):
            """Continuously send heart beat updates."""
            self.debug("Started keep alive loop.")
            fail_attempt = 0
            while True:
                try:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    await action()
                    fail_attempt = 0
                except asyncio.CancelledError:
                    self.debug("Stopped heartbeat loop")
                    break
                except asyncio.TimeoutError:
                    fail_attempt += 1
                    if fail_attempt >= 2:
                        self.debug("Heartbeat failed due to timeout, disconnecting")
                        break
                except Exception as ex:  # pylint: disable=broad-except
                    self.exception("Heartbeat failed (%s), disconnecting", ex)
                    break

            self.heartbeater = None
            if self.transport is not None:
                self.clean_up_session()

            self.debug("Stopped heartbeat loop")

        if self.heartbeater is None:
            # Prevent duplicates heartbeat task
            self.heartbeater = self.loop.create_task(
                keep_alive_loop(
                    # Ver. 3.3 gateways don't respond to subdevice query
                    self.subdevices_query
                    if is_gateway and self.version >= 3.4
                    else self.heartbeat
                )
            )

    def data_received(self, data):
        """Received data from device."""
        # self.debug("received data=%r", binascii.hexlify(data), force=True)
        self.dispatcher.add_data(data)

    def connection_lost(self, exc):
        """Disconnected from device."""
        self.debug("Connection lost: %s", exc, force=True)

        listener = self.listener and self.listener()
        self.clean_up_session()

        try:
            if listener is not None:
                listener.disconnected(exc or "Connection lost")
        except Exception:  # pylint: disable=broad-except
            self.exception("Failed to call disconnected callback")

    async def transport_write(self, data):
        """Write data on transport, ensure that no massive requests happen all at once."""
        wait = 0
        while self.last_command_sent < 0.050:
            await asyncio.sleep(0.010)
            wait += 1
            if wait >= 10:
                break

        self._last_command_sent = time.time()
        self.transport.write(data)

    async def close(self):
        """Close connection and abort all outstanding listeners."""
        self.debug("Closing connection")
        self.clean_up_session()

        if self.heartbeater:
            await self.heartbeater

        if self._sub_devs_query_task:
            await self._sub_devs_query_task

    def clean_up_session(self):
        """Clean up session."""
        self.debug(f"Cleaning up session.")
        self.real_local_key = self.local_key

        if self.heartbeater:
            self.heartbeater.cancel()

        if self._sub_devs_query_task:
            self._sub_devs_query_task.cancel()

        if self.is_connected:
            self.transport.close()

        if self.dispatcher:
            self.dispatcher.abort()

    async def exchange_quick(self, payload, recv_retries):
        """Similar to exchange() but never retries sending and does not decode the response."""
        if not self.is_connected:
            self.debug("send quick failed, could not get socket: %s", payload)
            return None
        enc_payload = (
            self._encode_message(payload)
            if isinstance(payload, MessagePayload)
            else payload
        )
        # self.debug("Quick-dispatching message %s, seqno %s", binascii.hexlify(enc_payload), self.seqno)

        try:
            await self.transport_write(enc_payload)
        except Exception:  # pylint: disable=broad-except
            return self.clean_up_session()

        while recv_retries:
            try:
                seqno = MessageDispatcher.SESS_KEY_SEQNO
                msg = await self.dispatcher.wait_for(seqno, payload.cmd)
                # for 3.4 devices, we get the starting seqno with the SESS_KEY_NEG_RESP message
                self.seqno = msg.seqno
            except Exception:  # pylint: disable=broad-except
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

    async def exchange(self, command, dps=None, nodeID=None, payload=None):
        """Send and receive a message, returning response from device."""
        if not self.is_connected:
            return None

        if self.version >= 3.4 and self.real_local_key == self.local_key:
            self.debug("3.4 or 3.5 device: negotiating a new session key")
            if not await self._negotiate_session_key():
                return self.clean_up_session()

        self.debug(
            "Sending command %s (device type: %s) DPS: %s", command, self.dev_type, dps
        )
        payload = payload or self._generate_payload(command, dps, nodeId=nodeID)
        real_cmd = payload.cmd
        dev_type = self.dev_type

        # Wait for special sequence number
        seqno = self.seqno

        if payload.cmd == HEART_BEAT:
            seqno = MessageDispatcher.HEARTBEAT_SEQNO
        elif payload.cmd == UPDATEDPS:
            seqno = MessageDispatcher.RESET_SEQNO
        elif payload.cmd == LAN_EXT_STREAM:
            seqno = MessageDispatcher.SUB_DEVICE_QUERY_SEQNO

        enc_payload = self._encode_message(payload)

        try:
            await self.transport_write(enc_payload)
        except Exception:  # pylint: disable=broad-except
            return self.clean_up_session()
        msg = await self.dispatcher.wait_for(seqno, payload.cmd)
        if msg is None:
            self.debug("Wait was aborted for seqno %d", seqno)
            return None

        # TODO: Verify stuff, e.g. CRC sequence number?
        if real_cmd in [HEART_BEAT, CONTROL, CONTROL_NEW] and len(msg.payload) == 0:
            # device may send messages with empty payload in response
            # to a HEART_BEAT or CONTROL or CONTROL_NEW command: consider them an ACK
            self.debug(f"ACK received for command {real_cmd}: ignoring: {msg.seqno}")
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
            return await self.exchange(command, dps, nodeID=nodeID)
        return payload

    async def status(self, cid=None):
        """Return device status."""
        status: dict = await self.exchange(command=DP_QUERY, nodeID=cid)

        self.dps_cache.setdefault("parent", {})
        if status and "dps" in status:
            if "cid" in status:
                self.dps_cache.update({status["cid"]: status["dps"]})
            else:
                self.dps_cache["parent"].update(status["dps"])

        return self.dps_cache.get(cid or "parent", {})

    async def heartbeat(self):
        """Send a heartbeat message."""
        return await self.exchange(HEART_BEAT)

    async def reset(self, dpIds=None, cid=None):
        """Send a reset message (3.3 only)."""
        if self.version == 3.3:
            self.dev_type = "type_0a"
            self.debug("reset switching to dev_type %s", self.dev_type)
            return await self.exchange(UPDATEDPS, dpIds, nodeID=cid)

        return True

    def set_updatedps_list(self, update_list):
        """Set the DPS to be requested with the update command."""
        self.dps_whitelist = update_list

    async def update_dps(self, dps=None, cid=None):
        """
        Request device to update index.

        Args:
            dps([int]): list of dps to update, default=detected&whitelisted
        """
        if self.version in UPDATE_DPS_LIST and self.is_connected:
            if dps is None:
                if not self.dps_cache:
                    await self.detect_available_dps(cid=cid)
                if self.dps_cache:
                    if cid and cid in self.dps_cache:
                        dps = [int(dp) for dp in self.dps_cache[cid]]
                    else:
                        dps = [int(dp) for dp in self.dps_cache["parent"]]
                    # filter non whitelisted dps
                    dps = list(set(dps).intersection(set(self.dps_whitelist)))
            payload = self._generate_payload(UPDATEDPS, dps, nodeId=cid)
            enc_payload = self._encode_message(payload)
            await self.transport_write(enc_payload)
        return True

    async def set_dp(self, value, dp_index, cid=None):
        """
        Set value (may be any type: bool, int or string) of any dps index.

        Args:
            dp_index(int):   dps index to set
            value: new value for the dps index
        """
        return await self.exchange(CONTROL, {str(dp_index): value}, nodeID=cid)

    async def set_dps(self, dps, cid=None):
        """Set values for a set of datapoints."""
        return await self.exchange(CONTROL, dps, nodeID=cid)

    async def subdevices_query(self):
        """Request a list of sub-devices and their status."""
        # Return payload: {"online": [cid1, ...], "offline": [cid2, ...]}
        # "nearby": [cids, ...] can come in payload.
        self.sub_devices_states = {"online": [], "offline": []}
        payload = self._generate_payload(
            LAN_EXT_STREAM, rawData={"cids": []}, reqType="subdev_online_stat_query"
        )

        return await self.exchange(command=LAN_EXT_STREAM, payload=payload)

    async def detect_available_dps(self, cid=None):
        """Return which datapoints are supported by the device."""
        # type_0d devices need a sort of bruteforce querying in order to detect the
        # list of available dps experience shows that the dps available are usually
        # in the ranges [1-25] and [100-170] need to split the bruteforcing in
        # different steps due to request payload limitation (max. length = 255)
        self.dps_cache = {}
        ranges = [
            (2, 11),
            (11, 21),
            (21, 31),
            (100, 110),
            (111, 121),
            (122, 130),
            (150, 160),
            (161, 170),
        ]

        for dps_range in ranges:
            # dps 1 must always be sent, otherwise it might fail in case no dps is found
            # in the requested range
            self.dps_to_request = {"1": None}
            self.add_dps_to_request(range(*dps_range))
            data = await self.status(cid=cid)
            if cid and cid in data:
                self.dps_cache.update({cid: data[cid]})
            elif not cid and "parent" in data:
                self.dps_cache.update({"parent": data["parent"]})

            if self.dev_type == "type_0a" and not cid:
                return self.dps_cache.get("parent", {})

        return self.dps_cache.get(cid or "parent", {})

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

            if self.version < 3.4:
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
                    return self.error_json(ERR_JSON, payload)

            if "data unvalid" in payload:
                if self.version <= 3.3:
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
            json_payload = self.error_json(ERR_JSON, payload)

            if "devid not" in payload:  # DeviceID Not found.
                raise ValueError(f"DeviceID [{self.id}] Not found")
            # else:
            #     raise DecodeError(
            #         f"[{self.id}]: could not decrypt data: wrong local_key? (exception: {ex}, payload: {payload})"
            #     )
            # json_payload = self.error_json(ERR_JSON, payload)

        # v3.4 stuffs it into {"data":{"dps":{"1":true}}, ...}
        if (
            "dps" not in json_payload
            and "data" in json_payload
            and "dps" in json_payload["data"]
        ):
            json_payload["dps"] = json_payload["data"]["dps"]

            if "cid" in json_payload["data"]:
                json_payload["cid"] = json_payload["data"]["cid"]

        # We will store the payload to trigger an event in HA.
        if "dps" in json_payload:
            self.dispatched_dps = json_payload["dps"]
        return json_payload

    async def _negotiate_session_key(self):
        self.remote_nonce = b""
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
        if self.version == 3.4:
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
        if self.version == 3.4:
            self.local_key = self.dispatcher.local_key = cipher.encrypt(
                self.local_key, False, pad=False
            )
        else:
            iv = self.local_nonce[:12]
            self.debug("Session IV: %r", iv)
            self.local_key = self.dispatcher.local_key = cipher.encrypt(
                self.local_key, use_base64=False, pad=False, iv=iv
            )[12:28]

        self.debug("Session key negotiate success! session key: %r", self.local_key)
        return True

    # adds protocol header (if needed) and encrypts
    def _encode_message(self, msg):
        hmac_key = None
        iv = None
        payload = msg.payload
        self.cipher = AESCipher(self.local_key)

        if self.version >= 3.4:
            hmac_key = self.local_key
            if msg.cmd not in NO_PROTOCOL_HEADER_CMDS:
                # add the 3.x header
                payload = self.version_header + payload
            self.debug("final payload for cmd %r: %r", msg.cmd, payload)

            if self.version >= 3.5:
                iv = True
                # seqno cmd retcode payload crc crc_good, prefix, iv
                msg = TuyaMessage(
                    self.seqno, msg.cmd, None, payload, 0, True, PREFIX_6699_VALUE, True
                )
                self.seqno += 1  # increase message sequence number
                data = pack_message(msg, hmac_key=self.local_key)
                self.debug("payload encrypted=%r", binascii.hexlify(data))
                return data

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
        msg = TuyaMessage(
            self.seqno, msg.cmd, 0, payload, 0, True, PREFIX_55AA_VALUE, False
        )
        self.seqno += 1  # increase message sequence number
        buffer = pack_message(msg, hmac_key=hmac_key)
        # self.debug("payload encrypted with key %r => %r", self.local_key, binascii.hexlify(buffer))
        return buffer

    def _generate_payload(
        self,
        command,
        data=None,
        gwId=None,
        devId=None,
        uid=None,
        nodeId=None,
        rawData=None,
        reqType=None,
    ):
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

        # Create a deep copy of payload_dict. otherwise, the original references will be overwritten
        def deepcopy_dict(_dict: dict):
            output = _dict.copy()
            for key, value in output.items():
                output[key] = deepcopy_dict(value) if isinstance(value, dict) else value
            return output

        payloads = deepcopy_dict(payload_dict)

        if command in payloads[self.dev_type]:
            if "command" in payloads[self.dev_type][command]:
                json_data = payloads[self.dev_type][command]["command"].copy()
            if "command_override" in payloads[self.dev_type][command]:
                command_override = payloads[self.dev_type][command]["command_override"]

        if self.dev_type != "type_0a":
            if (
                json_data is None
                and command in payloads["type_0a"]
                and "command" in payloads["type_0a"][command]
            ):
                json_data = payloads["type_0a"][command]["command"].copy()
            if (
                command_override is None
                and command in payloads["type_0a"]
                and "command_override" in payloads["type_0a"][command]
            ):
                command_override = payloads["type_0a"][command]["command_override"]

        if command_override is None:
            command_override = command
        if json_data is None:
            # I have yet to see a device complain about included but unneeded attribs, but they *will*
            # complain about missing attribs, so just include them all unless otherwise specified
            json_data = {"gwId": "", "devId": "", "uid": "", "t": "", "cid": ""}

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
        if "cid" in json_data:
            if cid := nodeId:
                json_data["cid"] = cid
                # for <= 3.3 we don't need `gwID`, `devID` and `uid` in payload.
                if command in (CONTROL, DP_QUERY):
                    for k in ("gwId", "devId", "uid"):
                        if k in json_data:
                            json_data.pop(k)
            else:
                del json_data["cid"]
        if "data" in json_data and "cid" in json_data["data"]:
            # "cid" is inside "data" For 3.4 and 3.5 versions.
            if cid := nodeId:
                json_data["data"]["cid"] = cid
            else:
                del json_data["data"]["cid"]
        if "t" in json_data:
            if json_data["t"] == "int":
                json_data["t"] = int(time.time())
            else:
                json_data["t"] = str(int(time.time()))
        if rawData is not None and "data" in json_data:
            json_data["data"] = rawData
        elif data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            elif "data" in json_data:
                json_data["data"]["dps"] = data  # We don't want to remove CID
            else:
                json_data["dps"] = data
        elif self.dev_type == "type_0d" and command == DP_QUERY:
            json_data["dps"] = self.dps_to_request
        if reqType and "reqType" in json_data:
            json_data["reqType"] = reqType

        if json_data == "":
            payload = ""
        else:
            payload = json.dumps(json_data)
        # if spaces are not removed device does not respond!
        payload = payload.replace(" ", "").encode("utf-8")
        self.debug("Sending payload: %s", payload)

        return MessagePayload(command_override, payload)

    def enable_debug(self, enable=False, friendly_name=None):
        """Enable the debug logs for the device."""
        self.set_logger(_LOGGER, self.id, enable, friendly_name)
        self.dispatcher.set_logger(_LOGGER, self.id, enable, friendly_name)

    @property
    def is_connected(self):
        return self.transport and not self.transport.is_closing()

    @property
    def last_command_sent(self):
        """Return last command sent by seconds"""
        return time.time() - self._last_command_sent

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
    try:
        _, protocol = await asyncio.wait_for(
            loop.create_connection(
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
            ),
            timeout=3,
        )
    # Assuming the connect timed out then then the host isn't reachable.
    except (OSError, TimeoutError) as ex:
        if ex.errno == errno.EHOSTUNREACH or isinstance(ex, TimeoutError):
            raise OSError(
                errno.EHOSTUNREACH,
                os.strerror(errno.EHOSTUNREACH) + f" ('{address}', '{port}')",
            )

        raise ex
    except (Exception, asyncio.CancelledError) as ex:
        raise ex
    except:
        raise Exception(f"The host refused to connect")

    await asyncio.wait_for(on_connected, timeout=timeout)
    return protocol
