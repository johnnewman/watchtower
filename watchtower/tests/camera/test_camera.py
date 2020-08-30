"""
These tests will require the camera to not be in use. Watchtower must be
terminated before running these.
"""

import cv2
import json
import os
import pytest
from watchtower.camera import SafeCamera

def test_bad_config():
    """
    Tests that initializing a SafeCamera instance with a bad config file path
    will still succeed.
    """
    camera = SafeCamera(name ="Test Camera",
                        resolution=(640, 480),
                        framerate=15,
                        config_path=os.path.join('dev', 'null'))
    camera.close()
    assert(camera)

def test_load_config_deletes_bad_data(tmp_config_path):
    """
    Tests that loading a config file with malformed data will remove the file
    from disk.
    """
    camera = SafeCamera(name ="Test Camera",
                        resolution=(640, 480),
                        framerate=15,
                        config_path=tmp_config_path)
    
    with open(tmp_config_path, 'w') as f:
        f.write('bad data')
    assert(os.path.exists(tmp_config_path))
    camera.load_config()
    assert(os.path.exists(tmp_config_path) == False)
    camera.close()

def test_load_config_reads_good_data(camera_with_existing_config):
    """
    Tests that initializing the camera with a config file path will load all of
    the provided fields in the config file.
    """
    camera = camera_with_existing_config
    assert(camera.awb_mode == 'shade')
    assert(camera.brightness == 75)
    assert(camera.contrast == -60)
    assert(camera.exposure_compensation == 5)
    assert(camera.exposure_mode == 'night')
    assert(camera.image_effect == 'solarize')
    assert(camera.iso == 0)
    assert(camera.meter_mode == 'average')
    assert(camera.rotation == 90)
    assert(camera.saturation == 50)
    assert(camera.sharpness == 25)
    assert(camera.video_denoise == True)
    camera.close()

def test_getting_config_params(camera_with_existing_config, sample_config_path):
    """
    Tests that `config_params()` returns the correct dictionary representation
    of the camera's configuration.
    """
    camera_config = camera_with_existing_config.config_params()
    camera_with_existing_config.close()

    sample_dict = None
    with open(sample_config_path, 'r') as f:
        sample_dict = json.load(f)
    
    assert(len(sample_dict) > 0)
    assert(len(sample_dict) == len(camera_config))
    for sample_key, sample_value in sample_dict.items():
        assert(camera_config[sample_key] == sample_value)


def test_updating_config_params(tmp_config_path):
    """
    Tests that `update_config_params()` will apply all of the provided fields
    to the camera's current configuration.
    """
    camera = SafeCamera(name ="Test Camera",
                        resolution=(640, 480),
                        framerate=15,
                        config_path=tmp_config_path)
    
    updates = dict(awb_mode='sunlight',
                   brightness=99,
                   contrast=4,
                   exposure_compensation=0,
                   exposure_mode='auto',
                   image_effect='none',
                   iso=0,
                   meter_mode='backlit',
                   rotation=0,
                   saturation=2,
                   sharpness=100,
                   video_denoise=False)
    camera.update_config_params(updates)

    assert(camera.awb_mode == 'sunlight')
    assert(camera.brightness == 99)
    assert(camera.contrast == 4)
    assert(camera.exposure_compensation == 0)
    assert(camera.exposure_mode == 'auto')
    assert(camera.image_effect == 'none')
    assert(camera.iso == 0)
    assert(camera.meter_mode == 'backlit')
    assert(camera.rotation == 0)
    assert(camera.saturation == 2)
    assert(camera.sharpness == 100)
    assert(camera.video_denoise == False)
    camera.close()

def test_updating_config_params_saves_to_disk(tmp_config_path, sample_config_path):
    """
    Tests that `update_config_params()` will write the updated camera
    configuration to disk.
    """
    camera = SafeCamera(name ="Test Camera",
                        resolution=(640, 480),
                        framerate=15,
                        config_path=tmp_config_path)

    updates = None
    with open(sample_config_path, 'r') as f:
        updates = json.load(f)
    
    camera.update_config_params(updates)
    camera.close()

    saved_data = None
    with open(tmp_config_path, 'r') as f:
        saved_data = json.load(f)

    assert(len(updates) > 0)
    assert(len(updates) == len(saved_data))
    for update_key, update_value in updates.items():
        assert(saved_data[update_key] == update_value)

# ---- Fixtures

@pytest.fixture
def camera_with_existing_config(sample_config_path):
    return SafeCamera(name ="Test Camera",
                      resolution=(640, 480),
                      framerate=15,
                      config_path=sample_config_path)

@pytest.fixture
def sample_config_path(test_data_path):
    return os.path.join(test_data_path, 'test_camera_config.json')

@pytest.fixture
def tmp_config_path(tmp_path):
    return os.path.join(tmp_path, 'camera_config.json')
