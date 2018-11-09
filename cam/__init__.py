import picamera
from threading import Lock


class SafeCamera (picamera.PiCamera):
    """
    A camera class that provides a safe mechanism for multiple threads to
    capture an image using ``safe_capture``.
    """

    def __init__(self, resolution, framerate):
        super(SafeCamera, self).__init__(resolution=resolution, framerate=framerate)
        self.__lock = Lock()

    def safe_capture(self, output, format='jpeg', use_video_port=True, downscale_factor=1):
        self.__lock.acquire()
        self.capture(output,
                     format=format,
                     use_video_port=use_video_port,
                     resize=tuple(int(i * downscale_factor) for i in self.resolution))
        self.__lock.release()

