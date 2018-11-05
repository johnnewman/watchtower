from threading import Thread, Lock
import time
import logging

MAX_READ_BYTES = int(1024*1024*2.5)  # 2.5 MB
READ_DATA_WAIT_TIME = 0.2  # Wait time for the next upload if data was read
EMPTY_WAIT_TIME = 0.5  # Wait time for next read if no data found


class StreamSaver(Thread):
    """
    A threaded class that loops over its stream in chunks and uploads read
    bytes into its ``byte_writer``.
    """

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
        self.stream = stream
        self.__byte_writer = byte_writer
        self.__lock = Lock()
        self.__stop_when_empty = stop_when_empty
        self.__stop = False
        self.name = name
        self.logger = logging.getLogger(__name__ + '.' + self.name)
        self.read_wait_time = READ_DATA_WAIT_TIME

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

    def start_pos(self):
        """
        Useful for subclasses for starting at a custom stream location.
        :return: The point where reading will begin.
        """
        return 0

    def read(self, position, length=MAX_READ_BYTES):
        """
        :param position: The position to start reading.
        :param length: The length of bytes to read.
        :return: a tuple of the bytes read and the position where reading
        stopped.
        """
        original_position = self.stream.tell()
        self.stream.seek(position)
        read_bytes = self.stream.read(length)
        self.stream.seek(original_position)  # Restore where the stream was
        if read_bytes is None:
            read_bytes = ''
        return read_bytes, position + len(read_bytes)

    def run(self):
        """
        Loops over the stream and calls ``read()`` to read bytes in chunks. All
        bytes are sent to the ``byte_writer``.

        Reading stops when either ``stop()`` is called or ``__stop_when_empty``
        is ``True`` and no bytes were read in the call to ``read()``.
        """
        try:
            stream_pos = self.start_pos()
            stopped = False
            total_bytes = 0
            while not stopped:
                read_bytes, stream_pos = self.read(stream_pos)
                total_bytes += len(read_bytes)
                stopped = self.__should_stop() or (self.__stop_when_empty and len(read_bytes) == 0)
                self.__byte_writer.append_bytes(read_bytes, stopped)
                self.logger.debug('Read %d bytes.' % len(read_bytes)) if len(read_bytes) > 0 else None
                if len(read_bytes) == 0:
                    time.sleep(EMPTY_WAIT_TIME)  # Wait for more data
                else:
                    time.sleep(self.read_wait_time)  # Avoid consuming the CPU
            self.logger.debug('Processed %d total bytes.' % total_bytes)

        except Exception as e:
            self.logger.exception('An exception occurred: %s' % e.message)
            try:
                self.__byte_writer.append_bytes('', close=True)  # Try to close if we have an exception
            except Exception as e2:
                self.logger.exception('Attempted to close the writer. Received an exception: %s' % e2.message)
