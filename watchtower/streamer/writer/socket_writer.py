import socket
from . import byte_writer


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
