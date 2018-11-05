import logging
import json
import re
import socket
import ssl
from threading import Thread
import time
from streamer.writer.socket_writer import SocketWriter, MJPEGSocketWriter
from streamer import MJPEGStreamSaver

TIMEOUT = 10

STATUS_ENDPOINT = 'status'
START_ENDPOINT = 'start'
STOP_ENDPOINT = 'stop'
STREAM_ENDPOINT = 'stream'


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
                 api_key=None,
                 api_key_header_name=None,
                 certfile=None,
                 keyfile=None,
                 mjpeg_rate_cap=2.5):
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
        self.__api_key = api_key
        self.__api_key_header_name = api_key_header_name
        self.__mjpeg_rate_cap = mjpeg_rate_cap
        self.__logger = logging.getLogger(__name__)
        if certfile is not None and keyfile is not None:
            print('Using SSL.')
            self.__context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.__context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        else:
            self.__context = None

    def verify_api_key(self, comm_socket, request):
        if self.__api_key is None:
            return True

        def write_forbidden():
            writer = SocketWriter(comm_socket)
            writer.append_bytes('HTTP/1.1 403 Forbidden\r\n\r\n', close=True)
            return False

        index = request.find('{}: {}'.format(self.__api_key_header_name, self.__api_key))
        if index == -1:
            self.__logger.warning('Bad API key supplied.')
            return write_forbidden()
        else:
            return True

    def get_endpoint(self, comm_socket, request):
        supported_endpoints = [STATUS_ENDPOINT, START_ENDPOINT, STOP_ENDPOINT, STREAM_ENDPOINT]
        re_result = re.match('^GET /(?P<endpoint>({}|{}|{}|{}))(\?|\s)'.format(*supported_endpoints), request)

        def write_not_found():
            writer = SocketWriter(comm_socket)
            writer.append_bytes('HTTP/1.1 404 Not Found\r\n\r\n', close=True)
            return None

        if re_result is None:
            self.__logger.warning('Did not find endpoint in the URL.')
            return write_not_found()
        elif re_result.group('endpoint') is None:
            self.__logger.warning('Regex \'endpoint\' does not exist.')
            return write_not_found()
        else:
            return re_result.group('endpoint')

    def handle_stream(self, comm_socket, request):
        re_result = re.match('^GET /{}(\?fps=(?P<fps>\d+\.?\d*))?'.format(STREAM_ENDPOINT), request)
        if re_result is None:
            self.__logger.info('No FPS supplied. Using 1.0.')
            fps = 1.0
        else:
            fps = re_result.group('fps')
            fps = float(fps)
            if fps == 0:
                self.__logger.warning('0 FPS supplied. Using 1.0.')
                fps = 1.0

        fps = min(fps, self.__mjpeg_rate_cap)
        self.__logger.info('Using FPS: %s' % str(fps))
        MJPEGStreamSaver(self.__get_camera_callback(),
                         byte_writer=MJPEGSocketWriter(comm_socket),
                         name='MJPEG',
                         rate=1.0/fps,
                         timeout=30).start()

    def handle_status_endpoint(self, comm_socket):
        writer = SocketWriter(comm_socket)
        writer.append_bytes('HTTP/1.1 200 OK\r\n\r\n')
        writer.append_bytes(json.dumps(dict(running=self.__get_running_callback())), close=True)

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

                request = comm_socket.recv(2048)
                if not self.verify_api_key(comm_socket, request):
                    continue
                endpoint = self.get_endpoint(comm_socket, request)
                if endpoint is None:
                    continue

                self.__logger.info('Hit endpoint: \'%s\'', endpoint)
                if endpoint == STATUS_ENDPOINT:
                    self.handle_status_endpoint(comm_socket)
                elif endpoint == STREAM_ENDPOINT:
                    self.handle_stream(comm_socket, request)
                elif endpoint == START_ENDPOINT:
                    self.__set_running_callback(True)
                    self.write_success(comm_socket)
                elif endpoint == STOP_ENDPOINT:
                    self.__set_running_callback(False)
                    self.write_success(comm_socket)
                else:  # Should not be possible after the endpoint regex.
                    self.__logger.warning('Unsupported message.')
                    comm_socket.shutdown(socket.SHUT_RDWR)
                    comm_socket.close()

            except Exception as e:
                self.__logger.exception('An exception occurred listening for commands: %s' % e.message)
                time.sleep(TIMEOUT)

    @staticmethod
    def write_success(comm_socket):
        writer = SocketWriter(comm_socket)
        writer.append_bytes('HTTP/1.1 200 OK\r\n\r\n', close=True)
