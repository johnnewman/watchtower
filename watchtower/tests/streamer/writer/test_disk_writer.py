import os
import pytest
from watchtower.streamer.writer.disk_writer import DiskWriter

TEST_FILE_NAME = 'test_file.bin'


def test_single_append_bytes(writer, random_data, tmp_path):
    writer.append_bytes(random_data, close=True)
    written_data = b''
    with open(os.path.join(tmp_path, TEST_FILE_NAME), 'rb') as f:
        written_data += f.read()
    assert(written_data == random_data)

def test_multiple_append_bytes(writer, random_data, tmp_path):
    append_count = 5
    amount_to_read = len(random_data)//append_count
    for i in range(append_count):
        data = random_data[i*amount_to_read:(i+1) * amount_to_read]
        writer.append_bytes(data, close=(i == append_count-1)) # Close on the last chunk.

    written_data = b''
    with open(os.path.join(tmp_path, TEST_FILE_NAME), 'rb') as f:
        written_data += f.read()
    assert(written_data == random_data)
    pass

# ---- Fixtures

@pytest.fixture
def writer(tmp_path):
    return DiskWriter(os.path.join(tmp_path, TEST_FILE_NAME))
