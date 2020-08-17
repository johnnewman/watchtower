import io
import os
import picamera
import pytest
import sys
import time
from threading import Lock

# Add watchtower to the path, which is needed by the fixtures.
watchtower_path = os.path.dirname(os.path.realpath(__file__))
for i in range(3):
    watchtower_path = os.path.split(watchtower_path)[0]
sys.path.insert(0, watchtower_path)

simulated_time = time.time()

def test_simulation(stream_saver):
    """
    Ensures that simulating frames and their timestamps along the stream will
    use expected values.
    """
    frame_count = 6
    stream_saver.stream.simulate_frames(frame_count)
    stream_saver.stream.simulate_timestamps(current_time=simulated_time,
                                            index_for_current_time=2)
    frames = stream_saver.stream.frames
    for frame in frames:
        print(frame)

    assert(len(frames) == 6)
    assert(frames[0].index == 0 and frames[0].position == 0 and frames[0].timestamp_sec() == int(simulated_time)-2)
    assert(frames[1].index == 1 and frames[1].position == 170 and frames[1].timestamp_sec() == int(simulated_time)-1)
    assert(frames[2].index == 2 and frames[2].position == 340 and frames[2].timestamp_sec() == int(simulated_time))
    assert(frames[3].index == 3 and frames[3].position == 510 and frames[3].timestamp_sec() == int(simulated_time)+1)
    assert(frames[4].index == 4 and frames[4].position == 680 and frames[4].timestamp_sec() == int(simulated_time)+2)
    assert(frames[5].index == 5 and frames[5].position == 850 and frames[5].timestamp_sec() == int(simulated_time)+3)

def test_beginning_start_pos(stream_saver):
    """
    Simulates the VideoStreamSaver's start time being on the first frame in the
    stream. The reading start position should be at 0.
    """
    stream_saver.stream.simulate_timestamps(current_time=simulated_time,
                                            index_for_current_time=0)
    assert(stream_saver.start_pos() == 0)

def test_middle_start_pos(stream_saver):
    """
    Simulates the VideoStreamSaver's start time being on the middle frame in
    the stream. The reading start position should be in the center.
    """
    assert(stream_saver.start_pos() == len(stream_saver.stream.getvalue())/2)

def test_read_from_beginning(stream_saver):
    """
    Ensures reading from frame 0 will read everything up to the last frame
    in the stream.
    """
    # Arrange
    stream_saver.stream.simulate_timestamps(current_time=simulated_time,
                                            index_for_current_time=0)
    last_frame = stream_saver.stream.frames[-1]

    # Act
    bytes_read, new_position = stream_saver.read(stream_saver.start_pos())
    
    #Assert
    assert(bytes_read == stream_saver.stream.getvalue()[0:last_frame.position])
    assert(new_position == len(bytes_read))

def test_read_from_middle(stream_saver):
    """
    Ensures reading from the middle frame will only read the last portion of
    the stream, up to the last frame in the stream.
    """
    # Arrange
    frame_count = 30
    stream_saver.stream.simulate_frames(frame_count)
    stream_saver.stream.simulate_timestamps(current_time=simulated_time,
                                            index_for_current_time=frame_count//2)
    last_frame = stream_saver.stream.frames[-1]
    middle_frame = stream_saver.stream.frames[frame_count//2]

    # Act
    read_position = stream_saver.start_pos()
    bytes_read, new_position = stream_saver.read(read_position)
    
    # Assert
    assert(read_position == middle_frame.position)
    assert(bytes_read == stream_saver.stream.getvalue()[read_position:last_frame.position])
    assert(new_position == (read_position + len(bytes_read)))

# ---- Fixtures

@pytest.fixture
def stream_saver(disk_writer):
    from watchtower.streamer.video_stream_saver import VideoStreamSaver

    simulated_frame_count = 16
    stream = MockPiCameraCircularIO(os.urandom(1024))
    stream.simulate_frames(simulated_frame_count)
    stream.simulate_timestamps(current_time=simulated_time,
                               index_for_current_time=simulated_frame_count/2)
    return VideoStreamSaver(stream, [disk_writer], "test stream saver", simulated_time)

@pytest.fixture
def disk_writer(tmpdir):
    from watchtower.streamer.writer.disk_writer import DiskWriter
    return DiskWriter(tmpdir + "/file.bin")

# ---- Mock objects

class MockPiCameraCircularIO(io.BytesIO):
    """
    This mock object is used because the real PiCameraCircularIO requires a
    camera instance.
    """
    def __init__(self, initial_bytes):
        self.frames = None
        self.lock = Lock()
        super(MockPiCameraCircularIO, self).__init__(initial_bytes)
    
    def simulate_frames(self, frame_count):
        """
        Creates mock frames that can be used in place of PiVideoFrame. These
        will be equally distributed through the stream.
        """
        mock_frames = []
        total_size = len(self.getvalue())
        for i in range(frame_count):
            frame = MockFrame(position=i*(total_size//frame_count),
                              index=i,
                              timestamp=0)
            mock_frames.append(frame)
            self.frames = mock_frames

    def simulate_timestamps(self, current_time, index_for_current_time):
        """
        Sets the timestamps on all frames to simulated values. Frames before
        index_for_current_time will be set to current_time - n, where n is the
        distance to index_for_current_time. Frames after index_for_current_time
        will be set to current_time + n, where n is the distance away from
        index_for_current_time.

        If there are 6 frames and index_for_current_time == 2:
        Frame 0 - (current_time - 2)
        Frame 1 - (current_time - 1)
        Frame 2 - (current_time)
        Frame 3 - (current_time + 1)
        Frame 4 - (current_time + 2)
        Frame 5 - (current_time + 3)
        """
        for i in range(len(self.frames)):
            frame = self.frames[i]
            if i <= index_for_current_time:
                frame.timestamp = (current_time - (index_for_current_time - i))
            else:
                frame.timestamp = (current_time + (i - index_for_current_time))
            frame.timestamp *= 1000000 # Timestamps are in microseconds.

class MockFrame:
    def __init__(self, position, index, timestamp):
        self.position = position
        self.index = index
        self.timestamp = timestamp
    
    def timestamp_sec(self):
        return self.timestamp//1000000

    def __repr__(self):
        rep = ("MockFrame index %i; position %i; timestamp (sec) %i" % \
            (self.index, self.position, self.timestamp_sec()))
        if self.timestamp_sec() == simulated_time:
            rep += " <-- current time"
        return rep
