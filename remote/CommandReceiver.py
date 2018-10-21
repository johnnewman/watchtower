import socket
import logging
from threading import Thread
import time

TIMEOUT = 10


class CommandReceiver(Thread):

    def __init__(self, set_running_callback, get_running_calback, port):
        super(CommandReceiver, self).__init__()
        self.__set_running_callback = set_running_callback
        self.__get_running_callback = get_running_calback
        self.__port = port

    def run(self):
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
                server_socket.listen(1)
                client_socket, address = server_socket.accept()
                message = client_socket.recv(1024).rstrip()
                logger.info('Received message \"%s\"' % message)

                def send_response(response):
                    total_sent = 0
                    while total_sent < len(response):
                        sent = client_socket.send(response[total_sent:])
                        if sent == 0:
                            raise RuntimeError('Socket connection is broken')
                        total_sent += sent

                if message == 'get_status':
                    if self.__get_running_callback():
                        send_response('monitoring')
                    else:
                        send_response('!monitoring')
                elif message == 'start_monitoring':
                    self.__set_running_callback(True)
                elif message == 'stop_monitoring':
                    self.__set_running_callback(False)
                else:
                    logger.warning('Received unknown message \"%s\"' % message)
                client_socket.close()

            except Exception as e:
                logger.exception('An exception occurred listening for commands: %s' % e.message)
                time.sleep(TIMEOUT)
