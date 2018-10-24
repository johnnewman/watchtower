from StreamSaver import StreamSaver


class CamStreamSaver(StreamSaver):

    def __init__(self, stream, byte_writer, name, start_time, stop_when_empty=False):
        super(CamStreamSaver, self).__init__(stream, byte_writer, name, stop_when_empty)
        self.__start_time = start_time

    def start_pos(self):
        """
        :return: The position of the most recent frame before ``__start_time``.
        """
        self.logger.debug('Using start_time %d' % self.__start_time)
        with self.stream.lock:  # Lock the live camera stream while searching
            start_frame = None
            for frame in self.stream.frames:
                if frame.timestamp is not None and frame.timestamp / 1000000 <= self.__start_time:
                    start_frame = frame
            if start_frame is not None:
                self.logger.debug('Found frame with timestamp: %d' % int(start_frame.timestamp / 1000000))
            else:
                self.logger.debug('Did not find a start frame.')
            return start_frame.position if start_frame is not None else 0

    def read(self, position, length=None):
        """
        Overridden so the camera stream can be locked while it is read. This
        will also find the distance to the last frame in the stream and
        use this as the length to read.
        """
        with self.stream.lock:  # Live camera stream needs to be locked while read
            last_frame = next(reversed(self.stream.frames))  # Read to the last frame.
            length = last_frame.position - position
            return super(CamStreamSaver, self).read(position, length)
