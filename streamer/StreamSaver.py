from threading import Thread, Lock
import time
import picamera

MAX_READ_BYTES = 1024*1024*5  # 5 MB
SLEEP_TIME = 0.5  # Seconds


class StreamSaver(Thread):

    def __init__(self, stream, byte_writer, name, stop_when_empty=False):
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
        self.__lock.acquire()
        self.__stop = True
        self.__lock.release()

    def run(self):
        try:
            # Returns bytes read at the position and the updated position
            def read_from_stream(position):
                cur_position = self.__stream.tell()
                if cur_position == position:
                    # print('[%s] Stream position has not moved. Not performing a read.' % self.name)
                    return '', position

                if position == -1:
                    position = 0
                    # print('[%s] Using stream start 0.' % self.name)

                self.__stream.seek(position)
                _read_bytes = self.__stream.read(MAX_READ_BYTES)  # Read from where we left off
                if _read_bytes is None:
                    _read_bytes = ''
                _stream_pos = position + len(_read_bytes)
                self.__stream.seek(cur_position)  # Restore where the stream was
                return _read_bytes, _stream_pos

            stream_pos = -1
            stopped = False
            total_bytes = 0
            while not stopped:
                # The live camera stream needs to be locked while we access it
                if isinstance(self.__stream, picamera.PiCameraCircularIO):
                    with self.__stream.lock:
                        if stream_pos == -1:
                            for frame in self.__stream.frames:
                                if frame.frame_type == picamera.PiVideoFrameType.sps_header:
                                    stream_pos = frame.position
                                    # print('[%s] Found first sps header at position %s' %
                                    #       (self.name, str(frame.position)))
                        read_bytes, stream_pos = read_from_stream(stream_pos)
                # Assuming the stream supports read() and seek()
                else:
                    read_bytes, stream_pos = read_from_stream(stream_pos)

                # print('[%s] read %s bytes.' % (self.name, str(len(read_bytes))))
                total_bytes += len(read_bytes)
                stopped = self.__should_stop() or (self.__stop_when_empty and len(read_bytes) == 0)
                self.__byte_writer.append_bytes(read_bytes, stopped)

                if len(read_bytes) == 0:
                    time.sleep(SLEEP_TIME)  # Wait for more data in the stream
            print('[%s] Processed %d bytes.' % (self.name, total_bytes))
        except Exception as e:
            print('[%s] An error occurred with stream: %s' % (self.name, e.message))
