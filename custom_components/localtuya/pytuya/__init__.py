# PyTuya Module
# -*- coding: utf-8 -*-
"""
 Python module to interface with Tuya WiFi smart devices
 Mostly derived from Shenzhen Xenon ESP8266MOD WiFi smart devices
 E.g. https://wikidevi.com/wiki/Xenon_SM-PW701U

 Author: clach04
 Maintained by: rospogrigio

 For more information see https://github.com/clach04/python-tuya

 Classes
    TuyaInterface(dev_id, address, local_key=None)
        dev_id (str): Device ID e.g. 01234567891234567890
        address (str): Device Network IP Address e.g. 10.0.1.99
        local_key (str, optional): The encryption key. Defaults to None.

 Functions 
    json = status()          # returns json payload
    set_version(version)     #  3.1 [default] or 3.3
    detect_available_dps()   # returns a list of available dps provided by the device
    add_dps_to_request(dps_index)  # adds dps_index to the list of dps used by the device (to be queried in the payload)
    set_dps(on, dps_index)   # Set value of any dps index.
    set_timer(num_secs):

        
 Credits
  * TuyaAPI https://github.com/codetheweb/tuyapi by codetheweb and blackrozes
    For protocol reverse engineering 
  * PyTuya https://github.com/clach04/python-tuya by clach04
    The origin of this python module (now abandoned)
  * LocalTuya https://github.com/rospogrigio/localtuya-homeassistant by rospogrigio
    Updated pytuya to support devices with Device IDs of 22 characters
"""

import base64
from hashlib import md5
from itertools import chain
import json
import logging
import socket
import sys
import time
import colorsys
import binascii

try:
    #raise ImportError
    import Crypto
    from Crypto.Cipher import AES  # PyCrypto
except ImportError:
    Crypto = AES = None
    import pyaes  # https://github.com/ricmoo/pyaes


version_tuple = (8, 1, 0)
version = version_string = __version__ = '%d.%d.%d' % version_tuple
__author__ = 'rospogrigio'

log = logging.getLogger(__name__)
logging.basicConfig()  # TODO include function name/line numbers in log
#log.setLevel(level=logging.DEBUG)  # Uncomment to Debug 

log.debug('%s version %s', __name__, version)
log.debug('Python %s on %s', sys.version, sys.platform)
if Crypto is None:
    log.debug('Using pyaes version %r', pyaes.VERSION)
    log.debug('Using pyaes from %r', pyaes.__file__)
else:
    log.debug('Using PyCrypto %r', Crypto.version_info)
    log.debug('Using PyCrypto from %r', Crypto.__file__)

SET = 'set'
STATUS = 'status'

PROTOCOL_VERSION_BYTES_31 = b'3.1'
PROTOCOL_VERSION_BYTES_33 = b'3.3'

IS_PY2 = sys.version_info[0] == 2

class AESCipher(object):
    def __init__(self, key):
        self.bs = 16
        self.key = key
    def encrypt(self, raw, use_base64 = True):
        if Crypto:
            raw = self._pad(raw)
            cipher = AES.new(self.key, mode=AES.MODE_ECB)
            crypted_text = cipher.encrypt(raw)
        else:
            _ = self._pad(raw)
            cipher = pyaes.blockfeeder.Encrypter(pyaes.AESModeOfOperationECB(self.key))  # no IV, auto pads to 16
            crypted_text = cipher.feed(raw)
            crypted_text += cipher.feed()  # flush final block
        #print('crypted_text (%d) %r' % (len(crypted_text), crypted_text))
        if use_base64:
            return base64.b64encode(crypted_text)
        else:
            return crypted_text
            
    def decrypt(self, enc, use_base64=True):
        if use_base64:
            enc = base64.b64decode(enc)
        #print('enc (%d) %r' % (len(enc), enc))
        #enc = self._unpad(enc)
        #enc = self._pad(enc)
        #print('upadenc (%d) %r' % (len(enc), enc))
        if Crypto:
            cipher = AES.new(self.key, AES.MODE_ECB)
            raw = cipher.decrypt(enc)
            #print('raw (%d) %r' % (len(raw), raw))
            return self._unpad(raw).decode('utf-8')
            #return self._unpad(cipher.decrypt(enc)).decode('utf-8')
        else:
            cipher = pyaes.blockfeeder.Decrypter(pyaes.AESModeOfOperationECB(self.key))  # no IV, auto pads to 16
            plain_text = cipher.feed(enc)
            plain_text += cipher.feed()  # flush final block
            return plain_text
    def _pad(self, s):
        padnum = self.bs - len(s) % self.bs
        return s + padnum * chr(padnum).encode()
    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]


def bin2hex(x, pretty=False):
    if pretty:
        space = ' '
    else:
        space = ''
    if IS_PY2:
        result = ''.join('%02X%s' % (ord(y), space) for y in x)
    else:
        result = ''.join('%02X%s' % (y, space) for y in x)
    return result


def hex2bin(x):
    if IS_PY2:
        return x.decode('hex')
    else:
        return bytes.fromhex(x)

# This is intended to match requests.json payload at https://github.com/codetheweb/tuyapi :
# type_0a devices require the 0a command as the status request
# type_0d devices require the 0d command as the status request, and the list of dps used set to null in the request payload (see generate_payload method)
payload_dict = {
  "type_0a": {
    "status": {
      "hexByte": "0a",
      "command": {"gwId": "", "devId": ""}
    },
    "set": {
      "hexByte": "07",
      "command": {"devId": "", "uid": "", "t": ""}
    },
    "prefix": "000055aa00000000000000",    # Next byte is command byte ("hexByte") some zero padding, then length of remaining payload, i.e. command + suffix (unclear if multiple bytes used for length, zero padding implies could be more than one byte)
    "suffix": "000000000000aa55"
  },
  "type_0d": {
    "status": {
      "hexByte": "0d",
      "command": {"devId": "", "uid": "", "t": ""}
    },
    "set": {
      "hexByte": "07",
      "command": {"devId": "", "uid": "", "t": ""}
    },
    "prefix": "000055aa00000000000000",    # Next byte is command byte ("hexByte") some zero padding, then length of remaining payload, i.e. command + suffix (unclear if multiple bytes used for length, zero padding implies could be more than one byte)
    "suffix": "000000000000aa55"
  }
}


class TuyaInterface(object):
    def __init__(self, dev_id, address, local_key, protocol_version, connection_timeout=10):
        """
        Represents a Tuya device.
        
        Args:
            dev_id (str): The device id.
            address (str): The network address.
            local_key (str, optional): The encryption key. Defaults to None.
            
        Attributes:
            port (int): The port to connect to.
        """

        self.id = dev_id
        self.address = address
        self.local_key = local_key.encode('latin1')
        self.connection_timeout = connection_timeout
        self.version = protocol_version
        self.dev_type = 'type_0a'
        self.dps_to_request = {}

        self.port = 6668  # default - do not expect caller to pass in

    def __repr__(self):
        return '%r' % ((self.id, self.address),)  # FIXME can do better than this

    def _send_receive(self, payload):
        """
        Send single buffer `payload` and receive a single buffer.
        
        Args:
            payload(bytes): Data to send.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(self.connection_timeout)
            s.connect((self.address, self.port))
        except Exception as e:
            print('Failed to connect to %s. Raising Exception.' % (self.address)) 
            raise e   
        try:
            s.send(payload)
        except Exception as e:
            print('Failed to send payload to %s. Raising Exception.' % (self.address)) 
            #s.close()
            raise e   

        try:
            data = s.recv(1024)
#            print("FIRST:  Received %d bytes" % len(data) )
        # sometimes the first packet does not contain data (typically 28 bytes): need to read again
            if len(data) < 40:
                time.sleep(0.1)
                data = s.recv(1024)
#                print("SECOND: Received %d bytes" % len(data) )
        except Exception as e:
            print('Failed to receive data from %s. Raising Exception.' % (self.address)) 
            #s.close()
            raise e   

        s.close()
        return data

    def detect_available_dps(self):
        # type_0d devices need a sort of bruteforce querying in order to detect the list of available dps 
        # experience shows that the dps available are usually in the ranges [1-25] and [100-110]
        # need to split the bruteforcing in different steps due to request payload limitation (max. length = 255)
        detected_dps = {}

        # dps 1 must always be sent, otherwise it might fail in case no dps is found in the requested range
        self.dps_to_request = {"1": None}
        self.add_dps_to_request(range(2, 11))
        try:
            data = self.status()
        except Exception as e:
            print("Failed to get status: [{}]".format(e))
            raise CannotConnect
        detected_dps.update( data["dps"] )

        if self.dev_type == "type_0a":
            return detected_dps

        self.dps_to_request = {"1": None}
        self.add_dps_to_request(range(11, 21))
        try:
            data = self.status()
        except Exception as e:
            print("Failed to get status: [{}]".format(e))
            raise CannotConnect
        detected_dps.update( data["dps"] )

        self.dps_to_request = {"1": None}
        self.add_dps_to_request(range(21, 31))
        try:
            data = self.status()
        except Exception as e:
            print("Failed to get status: [{}]".format(e))
            raise CannotConnect
        detected_dps.update( data["dps"] )

        self.dps_to_request = {"1": None}
        self.add_dps_to_request(range(100, 111))
        try:
            data = self.status()
        except Exception as e:
            print("Failed to get status: [{}]".format(e))
            raise CannotConnect
        detected_dps.update( data["dps"] )
#        print("DATA IS [{}] detected_dps [{}]".format(data,detected_dps))

        return detected_dps

    def add_dps_to_request(self, dps_index):
        if isinstance(dps_index, int):
            self.dps_to_request[str(dps_index)] = None
        else:
            self.dps_to_request.update({str(index): None for index in dps_index})

    def generate_payload(self, command, data=None):
        """
        Generate the payload to send.

        Args:
            command(str): The type of command.
                This is one of the entries from payload_dict
            data(dict, optional): The data to be send.
                This is what will be passed via the 'dps' entry
        """
        json_data = payload_dict[self.dev_type][command]['command']
        command_hb = payload_dict[self.dev_type][command]['hexByte']

        if 'gwId' in json_data:
            json_data['gwId'] = self.id
        if 'devId' in json_data:
            json_data['devId'] = self.id
        if 'uid' in json_data:
            json_data['uid'] = self.id  # still use id, no seperate uid
        if 't' in json_data:
            json_data['t'] = str(int(time.time()))

        if data is not None:
            json_data['dps'] = data
        if command_hb == '0d':
            json_data['dps'] = self.dps_to_request
#            log.info('******** COMMAND IS %r', self.dps_to_request)

        # Create byte buffer from hex data
        json_payload = json.dumps(json_data)
        #print(json_payload)
        json_payload = json_payload.replace(' ', '')  # if spaces are not removed device does not respond!
        json_payload = json_payload.encode('utf-8')
        log.debug('json_payload=%r', json_payload)
        #print('json_payload = ', json_payload, ' cmd = ', command_hb)

        if self.version == 3.3:
            self.cipher = AESCipher(self.local_key)  # expect to connect and then disconnect to set new
            json_payload = self.cipher.encrypt(json_payload, False)
            self.cipher = None
            if command_hb != '0a':
                # add the 3.3 header
                json_payload = PROTOCOL_VERSION_BYTES_33 + b"\0\0\0\0\0\0\0\0\0\0\0\0" + json_payload
        elif command == SET:
            # need to encrypt
            self.cipher = AESCipher(self.local_key)  # expect to connect and then disconnect to set new
            json_payload = self.cipher.encrypt(json_payload)
            preMd5String = b'data=' + json_payload + b'||lpv=' + PROTOCOL_VERSION_BYTES_31 + b'||' + self.local_key
            m = md5()
            m.update(preMd5String)
            hexdigest = m.hexdigest()
            json_payload = PROTOCOL_VERSION_BYTES_31 + hexdigest[8:][:16].encode('latin1') + json_payload
            self.cipher = None  # expect to connect and then disconnect to set new


        postfix_payload = hex2bin(bin2hex(json_payload) + payload_dict[self.dev_type]['suffix'])
        assert len(postfix_payload) <= 0xff
        postfix_payload_hex_len = '%x' % len(postfix_payload)  # TODO this assumes a single byte 0-255 (0x00-0xff)
        buffer = hex2bin( payload_dict[self.dev_type]['prefix'] + 
                          payload_dict[self.dev_type][command]['hexByte'] + 
                          '000000' +
                          postfix_payload_hex_len ) + postfix_payload

        # calc the CRC of everything except where the CRC goes and the suffix
        hex_crc = format(binascii.crc32(buffer[:-8]) & 0xffffffff, '08X')
        buffer = buffer[:-8] + hex2bin(hex_crc) + buffer[-4:]
        #print('full buffer(%d) %r' % (len(buffer), bin2hex(buffer, pretty=True) ))
        #print('full buffer(%d) %r' % (len(buffer), " ".join("{:02x}".format(ord(c)) for c in buffer)))
        return buffer
        
    def status(self):
        log.debug('status() entry (dev_type is %s)', self.dev_type)
        # open device, send request, then close connection
        payload = self.generate_payload('status')

        data = self._send_receive(payload)
        log.debug('status received data=%r', data)

        result = data[20:-8]  # hard coded offsets
        if self.dev_type != 'type_0a':
            result = result[15:]

        log.debug('result=%r', result)
        #result = data[data.find('{'):data.rfind('}')+1]  # naive marker search, hope neither { nor } occur in header/footer
        #print('result %r' % result)
        if result.startswith(b'{'):
            # this is the regular expected code path
            if not isinstance(result, str):
                result = result.decode()
            result = json.loads(result)
        elif result.startswith(PROTOCOL_VERSION_BYTES_31):
            # got an encrypted payload, happens occasionally
            # expect resulting json to look similar to:: {"devId":"ID","dps":{"1":true,"2":0},"t":EPOCH_SECS,"s":3_DIGIT_NUM}
            # NOTE dps.2 may or may not be present
            result = result[len(PROTOCOL_VERSION_BYTES_31):]  # remove version header
            result = result[16:]  # remove (what I'm guessing, but not confirmed is) 16-bytes of MD5 hexdigest of payload
            cipher = AESCipher(self.local_key)
            result = cipher.decrypt(result)
            print('decrypted result=[{}]'.format(result))
            log.debug('decrypted result=%r', result)
            if not isinstance(result, str):
                result = result.decode()
            result = json.loads(result)
        elif self.version == 3.3: 
            cipher = AESCipher(self.local_key)
            result = cipher.decrypt(result, False)
            log.debug('decrypted result=%r', result)
            if "data unvalid" in result:
                self.dev_type = 'type_0d'
                log.debug("'data unvalid' error detected: switching to dev_type %r", self.dev_type)
                return self.status()
            if not isinstance(result, str):
                result = result.decode()
            result = json.loads(result)
        else:
            log.error('Unexpected status() payload=%r', result)

        return result
    
    def set_dps(self, value, dps_index):
        """
        Set value (may be any type: bool, int or string) of any dps index.

        Args:
            dps_index(int):   dps index to set
            value: new value for the dps index
        """
        # open device, send request, then close connection
        if isinstance(dps_index, int):
            dps_index = str(dps_index)  # index and payload is a string

        payload = self.generate_payload(SET, {
            dps_index: value})
        
        data = self._send_receive(payload)
        log.debug('set_dps received data=%r', data)
        
        return data
    

    def set_timer(self, num_secs):
        """
        Set a timer.
        
        Args:
            num_secs(int): Number of seconds
        """
        # FIXME / TODO support schemas? Accept timer id number as parameter?

        # Dumb heuristic; Query status, pick last device id as that is probably the timer
        status = self.status()
        devices = status['dps']
        devices_numbers = list(devices.keys())
        devices_numbers.sort()
        dps_id = devices_numbers[-1]

        payload = self.generate_payload(SET, {dps_id:num_secs})

        data = self._send_receive(payload)
        log.debug('set_timer received data=%r', data)
        return data
