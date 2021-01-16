import io
import sys
from .stream_saver import StreamSaver
from ..remote.servo import Servo


class MJPEGStreamer(StreamSaver):
    """
    A streamer that captures individual JPEG frames from the camera.
    """

    def __init__(self, camera, byte_writers, name, servo=None, rate=1):
        super(MJPEGStreamer, self).__init__(stream=io.BytesIO(),
                                            byte_writers=byte_writers,
                                            name=name,
                                            stop_when_empty=False)
        self.__camera = camera
        self.__servo = servo
        self.read_wait_time = 1/rate

    def read(self, position, length=None):
        """
        Overridden to capture a new JPEG into the stream each call.

        :param position: Not used. Position will always be set to 0.
        :param length: Not used. The superclass is expected to read all the
        JPEG data.
        :return: The superclass data from ``read``.
        """
        self.stream.seek(0)  # Always reset to 0
        self.stream.truncate(0) # Dump the old data
        self.stream.write(self.__camera.jpeg_data)
        return super(MJPEGStreamer, self).read(0, length=sys.maxsize)

    def ended(self):
        """
        Overridden to flip the servo back off if the camera is not running.
        """
        
        super(MJPEGStreamer, self).ended()
        if not self.__camera.should_monitor and \
                self.__servo is not None:
            self.__servo.disable()
