import os
import pytest
import sys

test_data_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
watchtower_path = os.path.dirname(os.path.realpath(__file__))
for i in range(2):
    watchtower_path = os.path.split(watchtower_path)[0]
if watchtower_path not in sys.path:
    print('Inserted \"%s\" into system paths.' % watchtower_path)
    sys.path.insert(0, watchtower_path)


@pytest.fixture(scope="function")
def random_data():
    return os.urandom(1024*1024*10) # 10 megabytes

@pytest.fixture(scope="session")
def test_data_path():
    return test_data_dir

@pytest.fixture(scope="session")
def installation_path():
    return watchtower_path
