from threading import Thread, Lock
import time
import picamera
import logging

MAX_READ_BYTES = int(1024*1024*2.5)  # 2.5 MB
SLEEP_TIME = 0.5  # Seconds

global_index = 0
index_lock = Lock()


class StreamSaver(Thread):
    """
    A threaded class that loops over its stream in chunks and uploads read
    bytes into its ``byte_writer``."""

    def __init__(self, stream, byte_writer, name, stop_when_empty=False):
        """Initializes the streamer.

        :param stream: must respond to ``read()`` and ``seek()``. If it is a
        ``PiCameraCircularIO`` type, the ``lock`` will be used to ensure the
        camera doesn't modify the stream while it is read.
        :param byte_writer: should be a subclass of the ``ByteWriter`` class.
        :param name: should be unique for the steam. It is used for log
        statements.
        :param stop_when_empty: if True, the streamer will stop writing to the
        ByteWriter and will close the ByteWriter when it reaches the end of the
        stream. This is useful for finite streams.
        """
        super(StreamSaver, self).__init__()
        self.__stream = stream
        self.__byte_writer = byte_writer
        self.__lock = Lock()
        self.__stop_when_empty = stop_when_empty
        self.__stop = False
        self.name = name

    def __should_stop(self):
        self.__lock.acquire()
        should_stop = self.__stop
        self.__lock.release()
        return should_stop

    def stop(self):
        """
        Used to stop uploading. When set, the last array of bytes will be
        sent to the ``byte_writer`` with the ``close`` flag.  Finally, the
        thread will stop.
        """
        self.__lock.acquire()
        self.__stop = True
        self.__lock.release()

    def read_from_stream(self, position, length=MAX_READ_BYTES):
        """
        :param position: The position to start reading.
        :param length: The length of bytes to read.
        :return: a tuple of the bytes read and the position where reading
        stopped.
        """
        if position is None:
            position = 0
        original_position = self.__stream.tell()
        self.__stream.seek(position)
        read_bytes = self.__stream.read(length)
        self.__stream.seek(original_position)  # Restore where the stream was
        if read_bytes is None:
            read_bytes = ''
        return read_bytes, position + len(read_bytes)

    def run(self):
        """
        Loops over the stream and reads bytes in either ``MAX_READ_BYTES``
        sized chunks (if using a normal stream) or reads from the previous
        frame position to the newest frame (if using a camera stream.).  All
         bytes are sent to the ``byte_writer``.
         """

        global global_index
        logger = logging.getLogger(__name__ + '.' + self.name)
        try:
            index_lock.acquire()
            min_frame_index = global_index  # Start at a minimum of where the last streamer left off
            index_lock.release()

            stream_pos = None
            stopped = False
            total_bytes = 0
            while not stopped:
                if isinstance(self.__stream, picamera.PiCameraCircularIO):
                    with self.__stream.lock:  # Live camera stream needs to be locked while read
                        if stream_pos is None:
                            for frame in self.__stream.frames:
                                if frame.frame_type == picamera.PiVideoFrameType.sps_header:
                                    if stream_pos is None or frame.index <= min_frame_index:  # Find latest SPS header.
                                        stream_pos = frame.position
                            logger.debug('Newest SPS header is %d at position %d.' % (frame.index, stream_pos))
                        last_frame = next(reversed(self.__stream.frames))  # Read to the last frame.
                        min_frame_index = last_frame.index
                        end_pos = last_frame.position
                        logger.debug('Newest frame is %d at position %d.' % (last_frame.index, last_frame.position))
                        read_bytes, stream_pos = self.read_from_stream(stream_pos, length=end_pos-stream_pos)
                else:
                    read_bytes, stream_pos = self.read_from_stream(stream_pos)

                logger.debug('Read %d bytes.' % len(read_bytes)) if len(read_bytes) > 0 else None
                total_bytes += len(read_bytes)
                stopped = self.__should_stop() or (self.__stop_when_empty and len(read_bytes) == 0)
                self.__byte_writer.append_bytes(read_bytes, stopped)

                if len(read_bytes) == 0:
                    time.sleep(SLEEP_TIME)  # Wait for more data in the stream
            logger.info('Processed %d total bytes.' % total_bytes)

            index_lock.acquire()  # Update the min frame index for the next streamer.
            if min_frame_index > global_index:
                global_index = min_frame_index
                logger.debug('Updated the minimum frame index to %d.' % global_index)
            index_lock.release()

        except Exception as e:
            self.__byte_writer.append_bytes('', close=True)  # Try to close if we have an exception
            logger.exception('An exception occurred: %s' % e.message)
