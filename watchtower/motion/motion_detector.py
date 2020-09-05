import cv2 as cv
import datetime as dt
import logging
import time
from picamera.array import PiRGBArray

BASE_FRAME_RESET_INTERVAL = 45  # In seconds.
BLUR_SIZE = (21, 21)
DOWNSCALE_FACTOR = 0.25 # 25 percent of the normal resolution.
MOTION_COLOR = (0, 0, 255)
MOTION_BORDER = 2
MAX_THRESHOLD = 255


class MotionDetector:
    """
    A class that detects motion in the camera's feed.

    This implementation is based heavily on "Basic motion detection and
    tracking with Python and OpenCV" by Adrian Rosebrock.
    https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
    """

    def __init__(self, camera, sensitivity, min_area_perc):
        """
        Initializes the motion detector, but does not set the base frame.

        :param camera: The ``PiCamera`` instance setup for video recording.
        :param sensitivity: The sensitivity from 0 to 1. This affects the
        grayscale threshold calculation when determining the minimum difference
        between the reference frame and the current frame that will be detected
        as a motion pixel.
        :param min_area_perc: The percent of the total video resolution that
        must be detected as changed for a motion event to trigger.
        """
        self.__camera = camera
        self.min_delta = MAX_THRESHOLD - (sensitivity * MAX_THRESHOLD)
        self.min_area = camera.resolution[0] * camera.resolution[1] * (DOWNSCALE_FACTOR ** 2) * min_area_perc
        self.__base_frame = None
        self.__base_frame_date = dt.datetime.now()

    def capture_image(self):
        """
        Captures scaled down stills from the camera's video feed.
        :return: Returns a ``PiRGBArray`` of image data.
        """
        bgr_frame = PiRGBArray(self.__camera, size=tuple(int(i * DOWNSCALE_FACTOR) for i in self.__camera.resolution))
        self.__camera.safe_capture(bgr_frame, format='bgr', downscale_factor=DOWNSCALE_FACTOR)
        return bgr_frame

    def reset_base_frame_date(self):
        self.__base_frame_date = dt.datetime.now()

    def reset_base_frame(self):
        self.__base_frame = self.post_process_image(self.capture_image().array)
        self.reset_base_frame_date()
        logging.getLogger(__name__).debug('Updating base frame.')

    def detect(self):
        """
        Updates the base frame if ``BASE_FRAME_RESET_INTERVAL`` has passed.

        Compares two grayscale images: the base frame against the current
        camera frame. If big enough areas have changed, each of these areas are
        outlined.

        :return: a tuple containing a flag that indicates motion and the
        current frame jpg with motion areas outlined.
        """
        past_time_interval = (dt.datetime.now() - self.__base_frame_date).seconds > BASE_FRAME_RESET_INTERVAL
        need_new_base = past_time_interval or self.__base_frame is None
        if need_new_base:
            self.reset_base_frame()
            return False, None

        start_time = time.time()
        bgr_frame = self.capture_image()
        gray_frame = self.post_process_image(bgr_frame.array)

        # Compute the difference of the base frame and the current
        frame_delta = cv.absdiff(self.__base_frame, gray_frame)
        
        # Now filter the delta to only show high levels of change
        threshold = cv.threshold(frame_delta, self.min_delta, MAX_THRESHOLD, cv.THRESH_BINARY)[1]
        
        # Dilate the white threshold areas to bubble them together
        dilated = cv.dilate(threshold, None, iterations=2)
        
        # Find and separate all the dilated areas
        contours, _ = cv.findContours(dilated, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        contours = list(filter(lambda contour: cv.contourArea(contour) >= self.min_area, contours))

        # Draw the large countours onto the original image.
        for contour in contours:
            (x, y, w, h) = cv.boundingRect(contour)
            cv.rectangle(bgr_frame.array, (x, y), (x + w, y + h), color=MOTION_COLOR, thickness=MOTION_BORDER)
        
        jpg_bytes = cv.imencode('.jpg', bgr_frame.array)[1]
        logging.getLogger(__name__).debug('Time to process motion %.2f' % (time.time() - start_time))
        return len(contours) > 0, jpg_bytes

    def post_process_image(self, bgr_array):
        """
        Will gray and blur the bgr image data.
        """
        gray_array = cv.cvtColor(bgr_array, cv.COLOR_BGR2GRAY)
        return cv.GaussianBlur(gray_array, BLUR_SIZE, 0)
