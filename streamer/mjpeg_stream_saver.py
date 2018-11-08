import io
from stream_saver import StreamSaver
import time


class MJPEGStreamSaver(StreamSaver):

    def __init__(self, camera, byte_writer, name, rate=1, timeout=10):
        super(MJPEGStreamSaver, self).__init__(stream=io.BytesIO(),
                                               byte_writer=byte_writer,
                                               name=name,
                                               stop_when_empty=False)
        self.__timeout = timeout
        self.__camera = camera
        self.__start_time = None
        self.read_wait_time = rate

    def start(self):
        self.__start_time = time.time()
        super(MJPEGStreamSaver, self).start()

    def read(self, position, length=None):
        if time.time() - self.__start_time >= self.__timeout:
            self.logger.debug('Timeout of %ds reached. Stopping.' % self.__timeout)
            self.stop()

        self.stream.seek(0)  # Always reset to 0
        self.__camera.safe_capture(self.stream,
                                   downscale_factor=0.666)
        return super(MJPEGStreamSaver, self).read(0)
