from . import Recorder

class MJPEGRecorder(Recorder):
    """
    Special type of Recorder that will continuously stream an MJPEG feed and
    supply the most recent JPEG to the camera instance. This is a much faster
    way to capture stills than using the ``capture(...)`` function on PiCamera.
    """

    def create_stream(self, padding_sec):
        """
        Overridden since we don't use a stream. We only hold the raw jpeg data.
        """
        return None

    def start_recording(self):
        """
        Begins capturing MJPEG frames.
        """
        self.camera.start_recording(
            self,
            format='mjpeg',
            resize=self.resize_resolution,
            splitter_port=self.splitter_port
        )

    def stop_recording():
        """
        Call when Watchtower stops. Closes the connection with the camera.
        """
        self.camera.stop_recording(splitter_port=self.splitter_port)
    
    def persist(self, directory, start_time=0, frame=None):
        """
        Overridden to avoid persisting any mjpeg data. This is in memory only.
        """
        pass

    def stop_persisting(self):
        pass

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.camera.jpeg_data = buf

    def flush(self):
        pass
