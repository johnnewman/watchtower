import logging
import serial
from threading import Thread, Lock
import time
import Queue


class InfraredComm(Thread):
    """
    A thread class that can communicate with a micro controller to enable and
    disable infrared.
    """

    def __init__(self,
                 on_command,
                 off_command,
                 port,
                 baudrate,
                 timeout=1,
                 sleep_time=0.1):
        super(InfraredComm, self).__init__()
        self.__controller = serial.Serial(port=port,
                                          baudrate=baudrate,
                                          parity=serial.PARITY_NONE,
                                          stopbits=serial.STOPBITS_ONE,
                                          bytesize=serial.EIGHTBITS,
                                          timeout=timeout)
        self.__sleep_time = sleep_time
        self.__command_queue = Queue.Queue(1)
        self.__logger = logging.getLogger(__name__)
        self.__room_brightness = 1.0
        self.__on_command = on_command
        self.__off_command = off_command
        self.__lock = Lock()

    @property
    def room_brightness(self):
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
        self.__enqueue_command(self.__on_command)

    def turn_off(self):
        self.__enqueue_command(self.__off_command)

    def __enqueue_command(self, command):
        try:
            self.__command_queue.put(command)
        except Queue.Full:
            self.__logger.warn('Queue is full! Removing an element.')
            try:
                self.__command_queue.get_nowait()
            except Queue.Empty:
                pass
            self.__enqueue_command(command)  # Recursively try again.

    def __write_command(self, command):
        total_sent = 0
        while total_sent < len(command) and len(command) > 0:
            sent = self.__controller.write(command + '\n')
            if sent == 0:
                raise RuntimeError('Failed to write to serial port.')
            total_sent += sent

    def run(self):
        while True:
            # Attempt to write any new commands
            try:
                self.__write_command(self.__command_queue.get_nowait())
            except Queue.Empty:
                pass

            # Now read the light level
            if self.__controller.in_waiting() > 0:
                light_str = self.__controller.readline()
                try:
                    self.room_brightness = int(light_str)
                except TypeError:
                    self.__logger.warning('Failed to cast light string into an int.')
            time.sleep(self.__sleep_time)
