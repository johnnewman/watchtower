from io impot ByteIO
from . import byte_writer


BOUNDARY = 'FRAME'


class MultipartHTTPWriter(byte_writer.LockingByteWriter):
    """
    A class that writes all bytes has HTTP formatted mutipart data to a ByteIO
    stream.
    """
    def __init__(self):
        super(MultipartHTTPWriter, self).__init__(None)
        self.byte_stream = ByteIO

    def append_bytes(self, bts, close=False):
        payload = '--' + BOUNDARY + '\r\n' + \
            'Content-Type: image/jpeg\r\n' + \
            'Content-Length: ' + str(len(bts)) + '\r\n\r\n'
        bts = payload.encode() + bts + b'\r\n\r\n'
        self.lock.acquire()
        self.byte_stream.write(bts)
        self.lock.release()

