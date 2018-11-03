import logging
import re
import socket
import ssl
from threading import Thread
import time
from streamer.writer.SocketWriter import SocketWriter, MJPEGSocketWriter
from streamer import MJPEGStreamSaver

TIMEOUT = 10

STATUS_COMMAND = 'get_status'
START_COMMAND = 'start_running'
STOP_COMMAND = 'stop_running'
STREAM_ENDPOINT = '/stream'

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
                 min_mjpeg_rate=2.5):
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
        self.__min_mjpeg_rate = min_mjpeg_rate
        self.__logger = logging.getLogger(__name__)
        if certfile is not None and keyfile is not None:
            print('Using SSL.')
            self.__context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.__context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        else:
            self.__context = None

    def handle_stream(self, comm_socket, re_result):
        self.__logger.info('Received \"%s\".' % STREAM_ENDPOINT)
        fps = re_result.group('fps')
        try:
            if not isinstance(fps, float):
                fps = float(fps)
        except Exception:
            self.__logger.warning('Bad FPS supplied. Using 1.')
            fps = 1.0

        if fps == 0:
            self.__logger.warning('0 FPS supplied. Using 1.')
            fps = 1.0
        self.__logger.info('Using FPS: %s' % str(fps))
        MJPEGStreamSaver(self.__get_camera_callback(),
                         byte_writer=MJPEGSocketWriter(comm_socket),
                         name='MJPEG',
                         rate=max(fps, self.__min_mjpeg_rate),
                         timeout=30).start()

    def run(self):
        """
        Infinitely loops, waiting for socket connections and commands.
        """
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind(('', self.__port))
            self.__logger.debug('Waiting for a command on socket %d' % self.__port)
        except Exception as e:
            self.__logger.exception('An exception occurred setting up the server socket: %s' % e.message)
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
                self.__logger.info(message)
                stream_result = re.match('^GET {}\?(fps=(?P<fps>\d+))?'.format(STREAM_ENDPOINT), message)

                if message == STATUS_COMMAND:
                    self.__logger.info('Received \"%s\".' % STATUS_COMMAND)
                    writer = SocketWriter(comm_socket)
                    if self.__get_running_callback():
                        writer.append_bytes(RUNNING_RESPONSE, close=True)
                    else:
                        writer.append_bytes(NOT_RUNNING_RESPONSE, close=True)
                elif stream_result:
                    self.handle_stream(comm_socket, stream_result)
                else:
                    if message == START_COMMAND:
                        self.__logger.info('Received \"%s\".' % START_COMMAND)
                        self.__set_running_callback(True)
                    elif message == STOP_COMMAND:
                        self.__logger.info('Received \"%s\".' % STOP_COMMAND)
                        self.__set_running_callback(False)
                    else:
                        self.__logger.warning('Unsupported message.')
                    comm_socket.shutdown(socket.SHUT_RDWR)
                    comm_socket.close()

            except Exception as e:
                self.__logger.exception('An exception occurred listening for commands: %s' % e.message)
                time.sleep(TIMEOUT)
