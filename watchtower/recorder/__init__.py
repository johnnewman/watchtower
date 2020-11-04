import logging
import os
import picamera
from enum import Enum
from ..streamer.writer import dropbox_writer, disk_writer
from ..streamer import stream_saver, video_stream_saver


class Destination(Enum):
    """
    This enum represents one destination for a Recorder. Each Destination
    instance houses the necessary information for writing to that destination.
    """
    disk = 0
    dropbox = 1

    def __init__(self, value):
        self.file_chunk_size = -1
        self.token = None
        self.pem_path = None
        self.instance_path = None

    def create_writer(self, path, camera_name, video=True):
        """
        This function creates and returns a ByteWriter instance for the current
        destination.

        :param path: The path to write to. This is the recording day/time dir.
        :param camera_name: The camera's name which some destinations may need.
        :param video: Specifies whether the writer should be set up for video
        recording or jpeg recording (with False).
        """
        if self is Destination.disk:
            disk_path = os.path.join(self.instance_path, 'recordings', path)
            return disk_writer.DiskWriter(disk_path)
        else:
            return dropbox_writer.DropboxWriter(
                full_path='/'+os.path.join(camera_name, path),
                dropbox_token=self.token,
                file_chunk_size=self.file_chunk_size if video else -1,
                public_pem_path=self.pem_path if video else None
            )


class Recorder:
    """
    Instances of this class represent an active stream of the camera. Multiple
    Recorder instances can be used to capture various resolutions. This class
    can persist its stream's data to any number of Destination instances.
    """

    def __init__(self, camera, padding_sec, destinations, splitter_port=1, resize_resolution=None):
        """
        :param camera: the PiCamera used for recordings.
        :param padding_sec: the amount of time to record before a motion event.
        :param destinations: all Destination instances to use when persisting.
        :param splitter_port: the splitter port for the current recording. 1 is
        the primary port used. 0-4 are valid.
        :param resize_resolution: the resolution to resize from the camera's
        resolution. If used, this should be smaller than the camera resolution.
        """

        self.__camera = camera
        self.__destinations = destinations
        self.__resize_resolution = resize_resolution
        self.__splitter_port = splitter_port
        self.__stream = picamera.PiCameraCircularIO(
            camera,
            seconds=padding_sec,
            splitter_port=splitter_port
        )
        self.__stream_saver = None

    @property
    def splitter_port(self) -> int:
        return self.__splitter_port

    def start_recording(self):
        """
        Begins saving video data to an in-memory stream.
        """
        self.__camera.start_recording(
            self.__stream,
            format='h264',
            resize=self.__resize_resolution,
            splitter_port=self.__splitter_port
        )

    def stop_recording():
        """
        Call when Watchtower stops. Closes the connection with the camera.
        """
        self.__camera.stop_recording(splitter_port=self.__splitter_port)
    
    def persist(self, directory, start_time=0, frame=None):
        """
        Begins saving the recording to all destinations.

        :param directory: The recording day/time dir to write to.
        :param start_time: The time on which the recording should start. This
        is relative to when Watchtower was started.
        :param frame: A small stream containing jpg data. Useful for capturing
        the instant that the recording was triggered. This is sent to all
        destinations along with video.
        """
        if self.__stream_saver is not None:
            logging.getLogger(__name__).error('Call to persist() but already recording.')
            return None

        def create_writers(file_name, video=True):
            """
            Returns writers for all destinations using the specified file name.
            """
            return list(map(
                lambda dest: dest.create_writer(
                    path=os.path.join(directory, file_name),
                    camera_name=self.__camera.name,
                    video=video
                ),
                self.__destinations
            ))

        jpeg_writers = create_writers('trigger.jpg', video=False)
        jpeg_streamer = stream_saver.StreamSaver(
            stream=frame,
            byte_writers=jpeg_writers,
            name=('%s%s.jpeg' % (directory, self.__destinations)),
            stop_when_empty=True
        )
        jpeg_streamer.start()

        video_writers = create_writers('video.h264')
        self.__stream_saver = video_stream_saver.VideoStreamSaver(
            stream=self.__stream,
            byte_writers=video_writers,
            name=('%s%s.video' % (directory, self.__destinations)),
            start_time=start_time
        )
        self.__stream_saver.start()

    def stop_persisting(self):
        """
        Will stop saving the recording across all destinations.
        """
        if self.__stream_saver is None:
            logging.getLogger(__name__).error('Call to stop_persisting() but there are is no stream saver.')
            return
        self.__stream_saver.stop()
        self.__stream_saver = None
