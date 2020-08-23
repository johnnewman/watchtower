import cv2
import os
import picamera
import pytest
from watchtower.motion import motion_detector

TEST_RESOLUTION = (1640, 1232)


def test_detect_area_within_threshold(detector, tmp_path):
    """
    Uses some sample images to ensure motion is detected when the triggered
    area is within the size and sensitivity threshold.
    """
    # Set up the base frame
    motion, frame_jpg = detector.detect()
    assert(motion == False)
    assert(frame_jpg is None)

    # Now detect motion on the next frame
    motion, frame_jpg = detector.detect() 
    assert(motion)
    assert(frame_jpg is not None)
    output_path = os.path.join(tmp_path, 'motion.jpg')
    with open(output_path, 'wb') as f:
        f.write(frame_jpg)
        print('Saved motion jpg to %s' % output_path)
    
def test_detect_area_too_small(detector):
    """
    Sets the minimum area required for motion detection to a much larger value
    than the motion area in the test images. This should pass as no motion.
    """
    # Set the detector to trigger motion at 25% of the viewport
    min_area_perc = 0.25
    detector.min_area = TEST_RESOLUTION[0] * TEST_RESOLUTION[1] * (motion_detector.DOWNSCALE_FACTOR ** 2) * min_area_perc

    # Set up the base frame
    motion, frame_jpg = detector.detect()
    assert(motion == False)
    assert(frame_jpg is None)

    # Check for motion on the next frame and ensure nothing was detected.
    motion, frame_jpg = detector.detect() 
    assert(motion == False)
    assert(frame_jpg is not None)

def test_detect_low_sensitivity(detector, tmp_path):
    """
    Sets the sensitivity to a very low value that will not trigger motion using
    the test images.
    """
    sensitivity = 0.1
    detector.min_delta = motion_detector.MAX_THRESHOLD - (sensitivity * motion_detector.MAX_THRESHOLD)

    # Set up the base frame
    motion, frame_jpg = detector.detect()
    assert(motion == False)
    assert(frame_jpg is None)

    # Check for motion on the next frame and ensure nothing was detected.
    motion, frame_jpg = detector.detect() 
    assert(motion == False)
    assert(frame_jpg is not None)


# ---- Fixtures

@pytest.fixture
def detector(test_data_path):
    base_image = cv2.imread(os.path.join(test_data_path, 'test_scene.jpg'))
    motion_image = cv2.imread(os.path.join(test_data_path, 'test_motion.jpg'))
    camera = MockCamera(TEST_RESOLUTION, base_image, motion_image)
    return motion_detector.MotionDetector(camera, sensitivity=0.8, min_area_perc=0.02)

# ---- Mock Objects

class MockCamera:
    def __init__(self, resolution, base_image, motion_image):
        self.resolution = resolution
        self.base_image = base_image
        self.motion_image = motion_image
        self.__base_image_output = False

    def safe_capture(self, output, format='jpeg', use_video_port=True, downscale_factor=None):
        """
        This is the same `safe_capture()` method signature as in the SafeCamera
        class. This implementation ignores the `format` and `use_video_port`
        fields and will instead always write bgr image data to `output`.
        The `output` object must support calls to `write()` and `flush()`.
        
        The first time this method is called, the contents of `self.base_image`
        will be written to `output`. Subsequent calls will write the contents
        of `self.motion_image` to `output`.
        """
        new_resolution = self.resolution
        if downscale_factor is not None:
            new_resolution = tuple(int(i * downscale_factor) for i in self.resolution)

        # `raw_resolution` will round the resolution "up to the nearest
        # multiple of 32 horizontally and 16 vertically". This is normally done
        # by PiCamera. We must do it here in order to successfully flush a
        # PiRGBArray instance.
        new_resolution = picamera.array.raw_resolution(new_resolution)

        if not self.__base_image_output:
            output.write(cv2.resize(self.base_image, new_resolution))
            self.__base_image_output = True
        else:
            output.write(cv2.resize(self.motion_image, new_resolution))
        output.flush()
