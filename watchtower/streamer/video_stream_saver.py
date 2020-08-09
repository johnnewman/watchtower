import time
from .stream_saver import StreamSaver


class VideoStreamSaver(StreamSaver):
    """
    A StreamSaver that uses a camera stream. Safely locks the camera stream
    while accessing it. Also determines the best starting point to read the
    stream based on frame timestamps.
    """

    def __init__(self, stream, byte_writer, name, start_time, stop_when_empty=False):
        super(VideoStreamSaver, self).__init__(stream, byte_writer, name, stop_when_empty)
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
                is_before_start_time = frame.timestamp is not None and (frame.timestamp / 1000000) <= self.__start_time
                if start_frame is None or is_before_start_time:
                    start_frame = frame
            timestamp = (start_frame.timestamp / 1000000) if start_frame.timestamp is not None else 0
            self.logger.debug('Using frame with timestamp: %d' % timestamp)
            self.__last_streamed_frame = start_frame
            return start_frame.position

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
            start_time = time.time()
            last_streamed_index = self.__last_streamed_frame.index
            for frame in reversed(self.stream.frames):
                # We have to find the frame in the updated stream each time the
                # stream is read. In the case of a circular stream that's still
                # being written to, the frame will likely have a new position.
                self.__last_streamed_frame = frame
                if frame.index == last_streamed_index:
                    self.logger.debug('Time to find last frame: %.2f sec' % (time.time() - start_time))
                    break
            position = self.__last_streamed_frame.position
            last_frame = next(reversed(self.stream.frames))  # Read up to the last frame
            length = last_frame.position - self.__last_streamed_frame.position
            self.__last_streamed_frame = last_frame
            
            if length < 1000000: #1 mbit
                # Using read() uses less memory but consumes more CPU cycles.
                # To avoid blocking, only do this when the stream is small.
                bytes_read, new_position = super(VideoStreamSaver, self).read(position, length)
                self.logger.debug('Using built-in read() for length of %i bytes. Time: %.2f sec' % (length, time.time() - start_time))
                return bytes_read, new_position
            else:
                # Creating a copy of the stream via getvalue() will consume a
                # large amount of memory, depending on the stream's bitrate and
                # its total length in seconds. This is necessary because read()
                # is far too slow. A 30 mbit array can block for up to 30 sec.
                byte_array_copy = self.stream.getvalue()
                bytes_read = byte_array_copy[position:last_frame.position]
                self.logger.debug('Using byte copy of stream with length length of %i bytes. Time: %.2f sec' % (len(bytes_read), time.time() - start_time))
                return bytes_read, position + len(bytes_read)

    def ended(self):
        """
        Overridden to avoid the superclass implementation, which closes the
        stream. The live camera stream should never be closed.
        """