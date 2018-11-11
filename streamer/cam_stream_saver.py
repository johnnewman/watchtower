from stream_saver import StreamSaver


class CamStreamSaver(StreamSaver):
    """
    A StreamSaver that uses a camera stream. Safely locks the camera stream
    while accessing it. Also determines the best starting point to read the
    stream based on frame timestamps.
    """

    def __init__(self, stream, byte_writer, name, start_time, stop_when_empty=False):
        super(CamStreamSaver, self).__init__(stream, byte_writer, name, stop_when_empty)
        self.__start_time = start_time
        self.__last_streamed_frame = None

    def start_pos(self):
        """
        :return: The position of the most recent frame before ``__start_time``.
        """
        self.logger.debug('Using start timestamp %ds.' % self.__start_time)
        with self.stream.lock:
            start_frame = None
            for frame in self.stream.frames:
                if frame.timestamp is not None and (frame.timestamp / 1000000) <= self.__start_time:
                    start_frame = frame
                    self.__last_streamed_frame = start_frame
            if start_frame is not None:
                self.logger.debug('Found frame with timestamp: %d' % (start_frame.timestamp / 1000000))
            else:
                self.logger.debug('Did not find a start frame. Using 0 position.')
            return start_frame.position if start_frame is not None else 0

    def read(self, position, length=None):
        """
        Overridden to use the stream's ``frames`` property to locate the read
        position (useful if the stream is still being appended to) and compute
        the distance to the last frame in the stream.

        :param position: Not used because it is recalculated using the
        ``frames`` property of the stream.
        :param length: Not used because the length is computed using the last
        frame in the stream.
        :return: a tuple of the bytes read and the position where reading
        stopped.
        """
        with self.stream.lock:
            last_streamed_index = self.__last_streamed_frame.index
            for frame in reversed(self.stream.frames):
                # We have to find the frame in the updated stream each time the
                # stream is read. In the case of a circular stream that's still
                # being written to, the frame will likely have a new position.
                self.__last_streamed_frame = frame
                if frame.index == last_streamed_index:
                    break
            position = self.__last_streamed_frame.position
            last_frame = next(reversed(self.stream.frames))  # Read to the last frame
            length = last_frame.position - self.__last_streamed_frame.position
            self.__last_streamed_frame = last_frame
            return super(CamStreamSaver, self).read(position, length)

    def ended(self):
        """
        Overridden to avoid the superclass implementation, which closes the
        stream. The live camera stream should never be closed.
        """