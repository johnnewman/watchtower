from threading import Thread, Lock
import time
import picamera
import logging

MAX_READ_BYTES = 1024*1024*5  # 5 MB
SLEEP_TIME = 0.5  # Seconds


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
        """Used to stop uploading. When set, the last array of bytes will be
        sent to the ``byte_writer`` with the ``close`` flag.  Finally, the
        thread will stop."""

        self.__lock.acquire()
        self.__stop = True
        self.__lock.release()

    def run(self):
        """Loops over the stream, reads ``MAX_READ_BYTES`` chunks of bytes, and
        sends these to the ``byte_writer``."""

        logger = logging.getLogger(__name__ + '.' + self.name)
        try:
            # Returns bytes read at the position and the updated position
            def read_from_stream(stream, position):
                if position == -1:
                    position = 0
                    logger.debug('Using stream start 0.')

                __restore_position = stream.tell()
                stream.seek(position)
                __read_bytes = stream.read(MAX_READ_BYTES)  # Read from where we left off
                if __read_bytes is None:
                    __read_bytes = ''
                __stream_pos = position + len(__read_bytes)
                stream.seek(__restore_position)  # Restore where the stream was
                return __read_bytes, __stream_pos

            stream_pos = -1
            stopped = False
            total_bytes = 0
            while not stopped:
                if isinstance(self.__stream, picamera.PiCameraCircularIO):
                    with self.__stream.lock:  # Live camera stream needs to be locked while read
                        if stream_pos == -1:
                            for frame in self.__stream.frames:
                                if frame.frame_type == picamera.PiVideoFrameType.sps_header:
                                    stream_pos = frame.position
                                    logger.debug('Found first sps header at position %d' % frame.position)
                                    break
                        read_bytes, stream_pos = read_from_stream(self.__stream, stream_pos)
                else:
                    read_bytes, stream_pos = read_from_stream(self.__stream, stream_pos)

                logger.debug('Read %d bytes.' % len(read_bytes))
                total_bytes += len(read_bytes)
                stopped = self.__should_stop() or (self.__stop_when_empty and len(read_bytes) == 0)
                self.__byte_writer.append_bytes(read_bytes, stopped)

                if len(read_bytes) == 0:
                    time.sleep(SLEEP_TIME)  # Wait for more data in the stream
            logger.info('Processed %d bytes' % total_bytes)
        except Exception as e:
            # Try to close if we have an exception
            self.__byte_writer.append_bytes('', close=True)
            logger.exception('An exception occurred: %s' % e.message)
