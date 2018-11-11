import socket
from streamer.writer import byte_writer

BOUNDARY = 'FRAME'


class SocketWriter(byte_writer.ByteWriter):
    """
    A class that writes all bytes to its provided socket.
    """

    def __init__(self, comm_socket):
        super(SocketWriter, self).__init__(None)
        self.__socket = comm_socket

    def append_bytes(self, byte_string, close=False):
        """
        Writes the byte_string to the socket in its entirety. Any exception is
        thrown to the caller.
        :param byte_string: The string to write to the socket.
        :param close: When True, this will close the socket after writing.
        """
        total_sent = 0
        while total_sent < len(byte_string) and len(byte_string) > 0:
            sent = self.__socket.send(byte_string[total_sent:])
            if sent == 0:
                raise RuntimeError('Socket connection is broken.')
            total_sent += sent
        if close:
            self.__socket.shutdown(socket.SHUT_RDWR)
            self.__socket.close()


class MJPEGSocketWriter(SocketWriter):
    """
    A class that appends some HTTP header fluff to the byte string so a browser
    can interpret the data as an MJPEG stream. This string is sent to the
    superclass for output.
    """

    def __init__(self, comm_socket):
        super(MJPEGSocketWriter, self).__init__(comm_socket)
        self.__has_sent_header = False

    def append_bytes(self, byte_string, close=False):
        header_content = ''
        if not self.__has_sent_header:
            header_content = 'HTTP/1.1 200 OK\r\n' + \
                             'Content-Type: multipart/x-mixed-replace; boundary=' + BOUNDARY + '\r\n' + \
                             'Connection: keep-alive\r\n\r\n'
            self.__has_sent_header = True

        byte_string = header_content + '--' + BOUNDARY + '\r\n' + \
            'Content-Type: image/jpeg\r\n' + \
            'Content-Length: ' + str(len(byte_string)) + '\r\n\r\n' + \
            byte_string + \
            '\r\n\r\n'
        super(MJPEGSocketWriter, self).append_bytes(byte_string, close)


class ServoSocketWriter(SocketWriter):
    """
    A class that communicates with the PiServoServer. Simply used to set a
    servo's angle.
    """

    def __init__(self, servo_pin):
        self.__servo_pin = servo_pin
        comm_socket = socket.socket(socket.AF_INET)
        comm_socket.connect(("127.0.0.1", 9338))
        super(ServoSocketWriter, self).__init__(comm_socket)

    def send_angle(self, angle):
        self.append_bytes('%d %d' % (self.__servo_pin, angle), close=True)
