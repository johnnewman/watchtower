import picamera
from threading import Lock


class SafeCamera (picamera.PiCamera):
    def __init__(self, resolution, framerate):
        super(SafeCamera, self).__init__(resolution=resolution, framerate=framerate)
        self.__lock = Lock()

    def safe_capture(self, buf, format='jpeg', use_video_port=True, downscale_factor=1):
        self.__lock.acquire()
        self.capture(buf,
                     format=format,
                     use_video_port=use_video_port,
                     resize=tuple(int(i * downscale_factor) for i in self.resolution))
        self.__lock.release()

