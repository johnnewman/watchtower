import io
import sys
from streamer.stream_saver import StreamSaver
from streamer.writer import socket_writer

MJPEG_DOWNSCALE_FACTOR = 0.666


class MJPEGStreamer(StreamSaver):
    """
    A streamer that captures individual JPEG frames from the camera.
    """

    def __init__(self, camera, byte_writer, name, rate=1):
        super(MJPEGStreamer, self).__init__(stream=io.BytesIO(),
                                            byte_writer=byte_writer,
                                            name=name,
                                            stop_when_empty=False)
        self.__camera = camera
        self.read_wait_time = rate

    def read(self, position, length=None):
        """
        Overridden to capture a new JPEG into the stream each call.

        :param position: Not used. Position will always be set to 0.
        :param length: Not used. The superclass is expected to read all the
        JPEG data.
        :return: The superclass data from ``read``.
        """
        self.stream.seek(0)  # Always reset to 0
        self.__camera.safe_capture(self.stream,
                                   downscale_factor=MJPEG_DOWNSCALE_FACTOR)
        return super(MJPEGStreamer, self).read(0, length=sys.maxsize)

    def ended(self):
        """
        Overridden to flip the servo back off if the camera is not running.
        """
        super(MJPEGStreamer, self).ended()
        if not self.__camera.should_monitor:
            for servo in self.__camera.servos:
                socket_writer.ServoSocketWriter(servo.pin).send_angle(servo.angle_off)
