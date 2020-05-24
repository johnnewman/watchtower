import logging
import serial
from threading import Thread, Lock
import time
import queue


class InfraredComm(Thread):
    """
    A thread class that can communicate with a microcontroller to enable and
    disable infrared.  Serial commands are transmitted using utf-8 encoding.

    The brightness is read using an integer. Accessing and mutating the
    brightness is thread-safe.
    """

    def __init__(self,
                 on_command,
                 off_command,
                 port,
                 baudrate,
                 timeout=1,
                 sleep_time=0.1):
        """
        This sets up the serial connection but does not start data
        transmission.

        :param on_command: A string to send to the controller to turn on.
        :param off_command: A string to send to the controller to turn off.
        :param port: The port of the serial connection, like /dev/serial0.
        :param baudrate: The baudrate of the serial connection.
        :param timeout: The timeout for serial transmissions.
        :param sleep_time: The run loop sleep time. This should be equal to or
        less than the transmission interval of the microcontroller.
        """
        super(InfraredComm, self).__init__()
        self.__controller = serial.Serial(port=port,
                                          baudrate=baudrate,
                                          parity=serial.PARITY_NONE,
                                          stopbits=serial.STOPBITS_ONE,
                                          bytesize=serial.EIGHTBITS,
                                          timeout=timeout)
        self.__sleep_time = sleep_time
        self.__command_queue = queue.Queue(1)
        self.__logger = logging.getLogger(__name__)
        self.__room_brightness = 1.0
        self.__on_command = on_command
        self.__off_command = off_command
        self.__lock = Lock()

    @property
    def room_brightness(self):
        """
        :return: The brightness value read from the serial connection. This is
        an integer value.
        """
        self.__lock.acquire()
        brightness = self.__room_brightness
        self.__lock.release()
        return brightness

    @room_brightness.setter
    def room_brightness(self, value):
        self.__lock.acquire()
        self.__room_brightness = value
        self.__lock.release()

    def turn_on(self):
        """
        Sends the on command to the serial connection.
        """
        self.__enqueue_command(self.__on_command)

    def turn_off(self):
        """
        Sends the off command to the serial connection.
        """
        self.__enqueue_command(self.__off_command)

    def __enqueue_command(self, command):
        """
        Attempts to add the command string to the queue. If the queue is full,
        new commands take priority and the oldest command is removed.
        :param command: The command string to enqueue.
        """
        try:
            self.__command_queue.put(command)
        except queue.Full:
            self.__logger.warn('Queue is full! Removing an element.')
            try:
                self.__command_queue.get_nowait()
            except queue.Empty:
                pass
            self.__enqueue_command(command)  # Recursively try again.

    def __write_command(self, command):
        """
        Transmits the command string over the serial connection.
        :param command: The command string to transmit.
        """
        total_sent = 0
        while total_sent < len(command) and len(command) > 0:
            sent = self.__controller.write((command + '\n').encode())
            if sent == 0:
                raise RuntimeError('Failed to write to serial port.')
            total_sent += sent

    def run(self):
        """
        Infinitely loops, checking for new commands to transmit over the serial
        connection. Also reads the brightness each loop if there is serial data
        available.
        """
        while True:
            # Attempt to write any new commands
            try:
                self.__write_command(self.__command_queue.get_nowait())
            except queue.Empty:
                pass
            except RuntimeError as e:
                self.__logger.exception('Runtime exception: %s' % e)

            # Now read the light level
            if self.__controller.in_waiting > 0:
                light_str = self.__controller.readline()
                try:
                    self.room_brightness = int(light_str)
                except TypeError:
                    pass
                except ValueError:
                    pass
            time.sleep(self.__sleep_time)
