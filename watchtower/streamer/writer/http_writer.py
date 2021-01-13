import base64
from io import BytesIO
from . import byte_writer
import time
from threading import Lock, Event


MULTIPART_BOUNDARY = 'FRAME'


class HTTPMultipartWriter(byte_writer.ByteWriter):
    """
    A class that writes all bytes has HTTP formatted mutipart data to a BytesIO
    stream.
    """
    def __init__(self, use_base64=False):
        super(HTTPMultipartWriter, self).__init__(None)
        self.__bytes = b''
        self.__lock = Lock()
        self.__write_event = Event()
        self.__use_base64 = use_base64

    def append_bytes(self, bts, close=False):
        if self.__use_base64:
            bts = base64.standard_b64encode(bts)
        payload = '--' + MULTIPART_BOUNDARY + '\r\n' + \
            'Content-Type: image/jpeg\r\n' + \
            'Content-Length: ' + str(len(bts)) + '\r\n\r\n'
        bts = payload.encode() + bts + b'\r\n\r\n'
        with self.__lock:
            self.__bytes += bts
        self.__write_event.set()


    def blocking_read(self):
        self.__write_event.wait()
        with self.__lock:
            payload = self.__bytes
            self.__bytes = b''
        self.__write_event.clear()
        return payload

