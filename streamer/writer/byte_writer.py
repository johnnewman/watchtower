from abc import ABCMeta, abstractmethod


class ByteWriter:
    """
    Abstract class used to define an interface that ``streamer.StreamSaver``
    can use to pass bytes to a writer.
    """
    __metaclass__ = ABCMeta

    def __init__(self, full_path):
        self.full_path = full_path

    @abstractmethod
    def append_bytes(self, byte_string, close=False):
        pass
