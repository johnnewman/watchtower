import picamera
from collections import namedtuple
from threading import Lock

Servo = namedtuple('Servo', 'pin angle_on angle_off')


class SafeCamera (picamera.PiCamera):
    """
    A camera class that provides a safe mechanism for multiple threads to
    capture an image using ``safe_capture`` or get/set the monitoring status.
    It also contains an array of servos that can be turned on and off with the
    monitoring status.
    """

    def __init__(self, resolution, framerate, servos):
        super(SafeCamera, self).__init__(resolution=resolution, framerate=framerate)
        self.__should_monitor = True
        self.__should_record = False
        self.__lock = Lock()
        self.__servos = servos

    @property
    def servos(self):
        return self.__servos

    @property
    def should_record(self):
        self.__lock.acquire()
        should_record = self.__should_record
        self.__lock.release()
        return should_record

    @should_record.setter
    def should_record(self, value):
        self.__lock.acquire()
        self.__should_record = value
        self.__lock.release()

    @property
    def should_monitor(self):
        self.__lock.acquire()
        should_monitor = self.__should_monitor
        self.__lock.release()
        return should_monitor

    @should_monitor.setter
    def should_monitor(self, value):
        self.__lock.acquire()
        self.__should_monitor = value
        self.__lock.release()

    def safe_capture(self, output, format='jpeg', use_video_port=True, downscale_factor=None):
        self.__lock.acquire()
        new_resolution = None
        if downscale_factor is not None:
            new_resolution = tuple(int(i * downscale_factor) for i in self.resolution)
        self.capture(output,
                     format=format,
                     use_video_port=use_video_port,
                     resize=new_resolution)
        self.__lock.release()

