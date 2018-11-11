import json
import logging
import re
import socket
import ssl
import time
from streamer.writer.socket_writer import SocketWriter, MJPEGSocketWriter, ServoSocketWriter
from streamer import MJPEGStreamSaver
from threading import Thread

TIMEOUT = 3
STATUS_ENDPOINT = 'status'
START_ENDPOINT = 'start'
STOP_ENDPOINT = 'stop'
STREAM_ENDPOINT = 'stream'


class CommandServer(Thread):
    """
    A thread class that listens for HTTP messages over a socket. This supports
    SSL and client validation using headers.
    """

    def __init__(self,
                 port,
                 certfile,
                 keyfile,
                 api_key,
                 api_key_header_name,
                 camera,
                 mjpeg_rate_cap=2.5):
        """
        Initialized the server but does not open any ports until run() is
        called.

        :param port: The port to use to listen for commands.
        :param certfile: The path to the certfile for SSL.
        :param keyfile: The path to the keyfile for SSL.
        :param api_key: string to ensure connections from only a trusted client
        :param api_key_header_name: the name of the HTTP header field.
        :param camera: The camera instance for MJPEG streams and monitoring.
        :param mjpeg_rate_cap: The number of frames to send per second.
        """
        super(CommandServer, self).__init__()
        self.__port = port
        if certfile is not None and keyfile is not None:
            print('Using SSL.')
            self.__context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.__context.load_cert_chain(certfile=certfile, keyfile=keyfile)
        else:
            self.__context = None
        self.__api_key = api_key
        self.__api_key_header_name = api_key_header_name
        self.__camera = camera
        self.__mjpeg_rate_cap = mjpeg_rate_cap
        self.__logger = logging.getLogger(__name__)

    def verify_api_key(self, comm_socket, request):
        """
        Checks for the API key header in the supplied request data. This will
        be checked against the API key supplied to ``__init__``. Upon a
        failure, writes a 403 to the client and closes the connection.

        :param comm_socket: The socket to send 403's to if using a bad API key.
        :param request: The request string from the client.
        :return: A boolean indicating if the API key passed validation.
        """
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
        """
        Searches for a GET request to any of the supported endpoints.
        :param comm_socket:The socket to write 404s to if using a bad endpoint.
        :param request: The request string from the client.
        :return: The endpoint string requested or None.
        """
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
        """
        Parses the FPS out of the request string and creates a new MJPEG
        streamer using the supplied socket.
        :param comm_socket: The socket to send to the MJPEG streamer.
        :param request: The request string from the client.
        """
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

        if not self.__camera.should_monitor:
            self.expose_camera()
        MJPEGStreamSaver(self.__camera,
                         byte_writer=MJPEGSocketWriter(comm_socket),
                         name='MJPEG',
                         rate=1.0/fps).start()

    def send_status(self, comm_socket):
        """
        Writes the current running status as JSON to the socket and closes it.
        :param comm_socket: To socket to send the status.
        """
        writer = SocketWriter(comm_socket)
        writer.append_bytes('HTTP/1.1 200 OK\r\n\r\n')
        writer.append_bytes(json.dumps(dict(running=self.__camera.should_monitor)), close=True)

    def expose_camera(self):
        for servo in self.__camera.servos:
            ServoSocketWriter(servo.pin).send_angle(servo.angle_on)

    def hide_camera(self):
        for servo in self.__camera.servos:
            ServoSocketWriter(servo.pin).send_angle(servo.angle_off)

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
                    self.send_status(comm_socket)
                elif endpoint == STREAM_ENDPOINT:
                    self.handle_stream(comm_socket, request)
                elif endpoint == START_ENDPOINT:
                    self.expose_camera()
                    self.__camera.should_monitor = True
                    self.send_status(comm_socket)
                elif endpoint == STOP_ENDPOINT:
                    self.hide_camera()
                    self.__camera.should_monitor = False
                    self.send_status(comm_socket)

                else:  # Should not be possible after the endpoint regex.
                    self.__logger.warning('Unsupported message.')
                    comm_socket.shutdown(socket.SHUT_RDWR)
                    comm_socket.close()

            except Exception as e:
                self.__logger.exception('An exception occurred listening for commands: %s' % e.message)
                time.sleep(TIMEOUT)
