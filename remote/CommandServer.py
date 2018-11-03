import logging
import socket
from threading import Thread
import time
import ssl
from streamer.writer.SocketWriter import SocketWriter, MJPEGSocketWriter
from streamer import MJPEGStreamSaver

TIMEOUT = 10

STATUS_COMMAND = 'get_status'
START_COMMAND = 'start_running'
STOP_COMMAND = 'stop_running'
STREAM_COMMAND = 'stream'

RUNNING_RESPONSE = 'running'
NOT_RUNNING_RESPONSE = '!running'


class CommandServer(Thread):
    """
    A thread class that listens for commands over a socket. It uses callback
    functions as getters and setters for the responding object's running
    status.
    """

    def __init__(self,
                 get_camera_callback,
                 get_running_callback,
                 set_running_callback,
                 port,
                 certfile=None,
                 keyfile=None,
                 mjpeg_rate=2.5):
        """
        Initializes the command receiver but does not open any ports until
        ``run()`` is called.

        :param get_running_callback: Should be thread-safe
        :param set_running_callback: Should be thread-safe
        :param port: The port to use to listen for commands.
        """
        super(CommandServer, self).__init__()
        self.__get_camera_callback = get_camera_callback
        self.__get_running_callback = get_running_callback
        self.__set_running_callback = set_running_callback
        self.__port = port
        self.__mjpeg_rate = mjpeg_rate
        if certfile is not None and keyfile is not None:
            print('Using SSL.')
            self.__context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.__context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        else:
            self.__context = None

    def run(self):
        """
        Infinitely loops, waiting for socket connections and commands.
        """
        logger = logging.getLogger(__name__)
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind(('', self.__port))
            logger.debug('Waiting for a command on socket %d' % self.__port)
        except Exception as e:
            logger.exception('An exception occurred setting up the server socket: %s' % e.message)
            return

        while True:
            try:
                server_socket.listen(2)
                client_socket, address = server_socket.accept()

                if self.__context is not None:
                    comm_socket = self.__context.wrap_socket(client_socket, server_side=True)
                else:
                    comm_socket = client_socket

                message = comm_socket.recv(1024).rstrip()
                if message.startswith('GET /stream'):
                    message = STREAM_COMMAND

                if message == STATUS_COMMAND:
                    logger.info('Received \"%s\".' % STATUS_COMMAND)
                    writer = SocketWriter(comm_socket)
                    if self.__get_running_callback():
                        writer.append_bytes(RUNNING_RESPONSE, close=True)
                    else:
                        writer.append_bytes(NOT_RUNNING_RESPONSE, close=True)
                elif message == STREAM_COMMAND:
                    logger.info('Received \"%s\".' % STREAM_COMMAND)
                    MJPEGStreamSaver(self.__get_camera_callback(),
                                     byte_writer=MJPEGSocketWriter(comm_socket),
                                     name='MJPEG',
                                     rate=self.__mjpeg_rate,
                                     timeout=30).start()

                else:
                    if message == START_COMMAND:
                        logger.info('Received \"%s\".' % START_COMMAND)
                        self.__set_running_callback(True)
                    elif message == STOP_COMMAND:
                        logger.info('Received \"%s\".' % STOP_COMMAND)
                        self.__set_running_callback(False)
                    else:
                        logger.warning('Unsupported message.')
                    comm_socket.shutdown(socket.SHUT_RDWR)
                    comm_socket.close()

            except Exception as e:
                logger.exception('An exception occurred listening for commands: %s' % e.message)
                time.sleep(TIMEOUT)
