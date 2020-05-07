from abc import ABCMeta, abstractmethod
from threading import Lock


class ByteWriter:
    """
    Abstract class used to define an interface that ``streamer.StreamSaver``
    can use to pass bytes to a writer.
    """
    __metaclass__ = ABCMeta

    def __init__(self, full_path):
        self.full_path = full_path

    @abstractmethod
    def append_bytes(self, bts, close=False):
        pass

    def append_string(self, string, close=False):
        self.append_bytes(string.encode(), close)

class LockingByteWriter(ByteWriter):
    """
    Abstract class used to define an interface that ``streamer.StreamSaver``
    can use to pass bytes to a writer.
    """
    __metaclass__ = ABCMeta

    def __init__(self, full_path):
        super(LockingByteWriter, self).__init__(full_path)
        self.lock = Lock()

    @abstractmethod
    def append_bytes(self, bts, close=False):
        pass

    def append_string(self, string, close=False):
        self.append_bytes(string.encode(), close)
