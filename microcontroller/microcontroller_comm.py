import asyncio
import serial
import time
import queue

# Transmitted commands
INFRARED_ON_COMMAND = "ir_on"
INFRARED_OFF_COMMAND = "ir_off"
SERVO_COMMAND_PREFIX = "servo_angle_"

# Known responses
SUCCESS_MESSAGE = "ok"
REBOOT_MESSAGE = "reboot"
BRIGHTNESS_PREFIX = "bright: "


class MicrocontrollerComm:
    """
    A class that can communicate with a microcontroller to move a servo and
    enable or disable infrared lighting. Serial commands are transmitted using
    utf-8 encoding.
    """

    def __init__(self,
                 port,
                 baudrate,
                 transmission_interval=2):
        """
        Sets up the serial connection but does not start data transmission.

        :param port: The port of the serial connection, like "/dev/serial0".
        :param baudrate: The baud rate of the serial connection.
        :param transmission_interval: The interval at which commands are sent
        over the serial line.
        """
        super(MicrocontrollerComm, self).__init__()
        self.__controller = serial.Serial(port=port,
                                          baudrate=baudrate,
                                          parity=serial.PARITY_NONE,
                                          stopbits=serial.STOPBITS_ONE,
                                          bytesize=serial.EIGHTBITS,
                                          timeout=1)
        self.__command_queue = queue.Queue(2)
        self.__brightness = -1.0
        self.__infrared_running = False
        self.__transmission_interval = transmission_interval
        self.__last_transmission_time = 0

    @property
    def brightness(self):
        """
        :return: The brightness value read from the serial connection.
        """
        return self.__brightness

    @brightness.setter
    def brightness(self, value):
        self.__brightness = value

    @property
    def infrared_running(self):
        return self.__infrared_running

    @infrared_running.setter
    def infrared_running(self, value):
        old_value = self.__infrared_running
        self.__infrared_running = value
        
        # Send the command only if necessary.
        if value == True and old_value == False:
            self.__enqueue_command(INFRARED_ON_COMMAND)
        elif value == False and old_value == True:
            self.__enqueue_command(INFRARED_OFF_COMMAND)

    def set_servo_angle(self, angle):
        self.__enqueue_command(SERVO_COMMAND_PREFIX + str(angle))
    
    def __enqueue_command(self, command):
        """
        Attempts to add the command string to the queue. If the queue is full,
        new commands take priority and the oldest command is removed.
        :param command: The command string to enqueue.
        """
        try:
            self.__command_queue.put(command)
        except queue.Full:
            print('Queue is full! Removing an element.')
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
        print(f'Transmitted \"{command}\".')

    def __process_input(self):
        """
        Checks for input on the serial connection and handles any messages
        received. Returns True if the response was a success message. These
        should be received after transmitting a command.
        """
        if self.__controller.in_waiting > 0:
            response = self.__controller.readline().decode("utf-8").strip()
            if response == SUCCESS_MESSAGE:
                print(f'Received an \"{SUCCESS_MESSAGE}\" message!')
                return True
            elif response == REBOOT_MESSAGE:
                print('Microcontroller has rebooted.')
            elif response.startswith(BRIGHTNESS_PREFIX):
                try:
                    self.__infrared_running = True
                    self.brightness = int(response[len(BRIGHTNESS_PREFIX):])
                except Exception as e:
                    print(f'Exception parsing brightness: {e}')
        return False

    async def loop(self):
        """
        Infinitely loops, checking for new commands to transmit over the serial
        connection while also processing any input data from the connection.
        """
        while True:
            wait_for_success_message = False

            # Only transmit at the transmission interval so that the receiving
            # end has time to process each command.
            if time.time() - self.__last_transmission_time >= 1.0/self.__transmission_interval:
                try:
                    # Attempt to transmit any new commands
                    command = self.__command_queue.get_nowait()
                    self.__write_command(command)
                    wait_for_success_message = True
                    self.__last_transmission_time = time.time()
                except queue.Empty:
                    pass
                except RuntimeError as e:
                    print(f'Runtime exception: {e}')

            # Now handle any input
            if not self.__process_input() and wait_for_success_message:
                # Wait for the next transmission
                await asyncio.sleep(1.0/self.__transmission_interval)
                if not self.__process_input():
                    print(f'Did not receive success code for command \"{command}\". Retrying.')
                    self.__enqueue_command(command)
            
            await asyncio.sleep(1.0/self.__transmission_interval/2.0)
