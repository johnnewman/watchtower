import socket
from . import byte_writer

BOUNDARY = 'FRAME'


class SocketWriter(byte_writer.ByteWriter):
    """
    A class that writes all bytes to its provided socket.
    """

    def __init__(self, comm_socket):
        super(SocketWriter, self).__init__(None)
        self.__socket = comm_socket

    def append_bytes(self, bts, close=False):
        """
        Writes the bytes to the socket in its entirety. Any exception is
        thrown to the caller.
        :param byts: The bytes object to write to the socket.
        :param close: When True, this will close the socket after writing.
        """
        total_sent = 0
        while total_sent < len(bts) and len(bts) > 0:
            sent = self.__socket.send(bts[total_sent:])
            if sent == 0:
                raise RuntimeError('Socket connection is broken.')
            total_sent += sent
        if close:
            self.__socket.shutdown(socket.SHUT_RDWR)
            self.__socket.close()


class MJPEGSocketWriter(SocketWriter):
    """
    A class that appends some HTTP header data to the byte string to make it a
    proper HTTP MJPEG stream. This string is sent to the superclass for output.
    """

    def __init__(self, comm_socket):
        super(MJPEGSocketWriter, self).__init__(comm_socket)
        self.__has_sent_header = False

    def append_bytes(self, bts, close=False):
        header_content = ''
        if not self.__has_sent_header:
            header_content = 'HTTP/1.1 200 OK\r\n' + \
                             'Content-Type: multipart/x-mixed-replace; boundary=' + BOUNDARY + '\r\n' + \
                             'Connection: keep-alive\r\n\r\n'
            self.__has_sent_header = True
        
        payload = header_content + '--' + BOUNDARY + '\r\n' + \
            'Content-Type: image/jpeg\r\n' + \
            'Content-Length: ' + str(len(bts)) + '\r\n\r\n'

        super(MJPEGSocketWriter, self).append_bytes(payload.encode(), False)
        super(MJPEGSocketWriter, self).append_bytes(bts, False)
        super(MJPEGSocketWriter, self).append_bytes('\r\n\r\n'.encode(), close)

class MJPEGSocketWriterTwo(MJPEGSocketWriter):

    def __init__(self):
        super(MJPEGSocketWriterTwo, self).__init__(None)



class ServoSocketWriter(SocketWriter):
    """
    A class that communicates with PiServoServer. Used to set a servo's angle.
    """

    def __init__(self, servo_pin):
        self.__servo_pin = servo_pin
        comm_socket = socket.socket(socket.AF_INET)
        comm_socket.connect(("127.0.0.1", 9338))
        super(ServoSocketWriter, self).__init__(comm_socket)

    def send_angle(self, angle):
        self.append_string('%d %d' % (self.__servo_pin, angle), close=True)
