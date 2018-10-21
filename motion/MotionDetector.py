from picamera.array import PiRGBArray
import cv2
import datetime as dt
import logging

BASE_FRAME_RESET_INTERVAL = 45  # Seconds. Also serves as the minimum event time.
logger = None

# This implementation is based heavily on "Basic motion detection and tracking with Python and OpenCV"
# by Adrian Rosebrock.
# https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/


class MotionDetector:

    def __init__(self, camera, min_delta, min_area):
        self.__camera = camera
        self.min_delta = min_delta
        self.min_area_px = camera.resolution[0] * camera.resolution[1] * min_area / 2
        self.__base_frame = None
        self.__base_frame_date = dt.datetime.now()

    def capture_image(self):
        bgr_frame = PiRGBArray(self.__camera, size=self.__camera.resolution)
        self.__camera.capture(bgr_frame, format='bgr', use_video_port=True)
        return bgr_frame

    def reset_base_frame_date(self):
        self.__base_frame_date = dt.datetime.now()

    def __reset_base_frame(self):
        global logger
        self.__base_frame = self.post_process_image(self.capture_image().array)
        self.reset_base_frame_date()

        if logger is None:
            logger = logging.getLogger(__name__)
        logger.info('Updating base frame.')

    def detect(self):
        past_time_interval = (dt.datetime.now() - self.__base_frame_date).seconds > BASE_FRAME_RESET_INTERVAL
        need_new_base = past_time_interval or self.__base_frame is None
        if need_new_base:
            self.__reset_base_frame()
            return False, None

        bgr_frame = self.capture_image()
        current_frame = self.downsize_image(bgr_frame.array)
        gray_frame = self.post_process_image(bgr_frame.array)

        # Compute the difference of the base frame and the current
        frame_delta = cv2.absdiff(self.__base_frame, gray_frame)
    #        cv2.imwrite('delta.jpg', frame_delta)

        # Now filter the delta to only show high levels
        threshold = cv2.threshold(frame_delta, self.min_delta, 255, cv2.THRESH_BINARY)[1]
    #       cv2.imwrite('thresh.jpg', threshold)

        # Dilate the white threshold areas to bubble them together
        dilated = cv2.dilate(threshold, None, iterations=2)
    #        cv2.imwrite('dilated.jpg', threshold)

        # Find and separate all the white areas
        contours = cv2.findContours(dilated.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]

        # Iterate over every contour and find the ones over the min area
        motion = False
        for contour in contours:
            if cv2.contourArea(contour) > self.min_area_px:
                motion = True
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(current_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        return motion, cv2.imencode('.jpg', current_frame)[1]

    def downsize_image(self, image_array):
        return cv2.resize(image_array, tuple(i/2 for i in self.__camera.resolution), interpolation=cv2.INTER_AREA)

    # Will gray and blur the bgr image data
    def post_process_image(self, bgr_array):
        bgr_array = self.downsize_image(bgr_array)
        gray_array = cv2.cvtColor(bgr_array, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray_array, (21, 21), 0)
