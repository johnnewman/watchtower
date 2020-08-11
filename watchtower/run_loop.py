
from collections import namedtuple
from flask import Flask
from threading import Thread
import datetime as dt
import io
import logging
import os
import picamera
import time
from .camera import SafeCamera
from .motion.motion_detector import MotionDetector
from .remote.servo import Servo
from .streamer import video_stream_saver as streamer
from .streamer.writer import dropbox_writer, disk_writer

WAIT_TIME = 0.1
INITIALIZATION_TIME = 3  # In Seconds
MOTION_INTERVAL_WHILE_SAVING = 1.0  # In Seconds


class RunLoop(Thread):
    """
    This is the central threaded class for Watchtower that is started when the
    Flask app is initialized. It starts a continuous camera stream and waits
    for motion to be detected. Once motion is detected, the triggered frame
    and associated video are saved to disk. The same files can be encrytped and
    sent to Dropbox when configured to do so in the watchtower_config file.
    """

    def __init__(self, app):
        super(RunLoop, self).__init__()

        if app.config.get('MICRO_ENABLED') == True:
            self.__micro_comm = self.setup_microcontroller_comm(app)
        else:
            self.__micro_comm = None
            self.servo = None

        self.camera = self.setup_camera(app)
        
        motion_config = app.config.get_namespace('MOTION_')
        area = motion_config['min_trigger_area']
        delta = motion_config['pixel_delta_trigger']
        self.__padding = motion_config['recording_padding']
        self.__max_event_time = motion_config['max_event_time']
        self.__motion_detector = MotionDetector(self.camera, delta, area)
        self.__stream = picamera.PiCameraCircularIO(self.camera, seconds=(self.__padding))

        self.__start_time = None
        self.__day_format = app.config['DIR_DAY_FORMAT']
        self.__time_format = app.config['DIR_TIME_FORMAT']
        self.__video_date_format = app.config['VIDEO_DATE_FORMAT']
        self.__dropbox_config  = app.config.get_namespace('DROPBOX_')
        self.__instance_path = app.instance_path

    @property
    def servo(self) -> Servo:
        return self.__servo

    @servo.setter
    def servo(self, value):
        self.__servo = value

    @property
    def start_time(self):
        return self.__start_time

    def setup_microcontroller_comm(self, app):
        from .remote.microcontroller_comm import MicrocontrollerComm
        controller_config = app.config.get_namespace('MICRO_')
        controller = MicrocontrollerComm(port=controller_config['port'],
                                         baudrate=controller_config['baudrate'],
                                         transmission_interval=controller_config['transmission_freq'])
        controller.start()

        angle_on = controller_config['servo_angle_on']
        angle_off = controller_config['servo_angle_off']
        if angle_on is not None and angle_off is not None:
            self.servo = Servo(angle_on,
                               angle_off,
                               controller)
         
        return controller

    def setup_camera(self, app):
        camera = SafeCamera(name = app.config["CAMERA_NAME"],
                            resolution=tuple(app.config['VIDEO_SIZE']),
                            framerate=app.config['VIDEO_FRAMERATE'])
        camera.rotation = app.config.get('VIDEO_ROTATION')
        camera.annotate_background = picamera.Color('black')
        camera.annotate_text_size = 14
        return camera

    def wait(self):
        """Briefly waits on the camera and updates the annotation on the feed."""

        date_string = dt.datetime.now().strftime(self.__video_date_format)
        text = '{} | {}'.format(self.camera.name, date_string)
        if self.__micro_comm is not None:
            text = text + ' | Brightness: ' + str(self.__micro_comm.room_brightness)
        self.camera.annotate_text = text
        self.camera.wait_recording(WAIT_TIME)

    def save_stream(self, stream, path, debug_name, stop_when_empty=False):
        """Saves the ``stream`` to disk and optionally Dropbox, if Dropbox
        configurations were supplied in the config file."""

        stream_start_time = max(0, int(time.time() - self.start_time - self.__padding))

        def create_cam_stream(byte_writers):
            return streamer.VideoStreamSaver(stream=stream,
                                             byte_writers=byte_writers,
                                             name=debug_name,
                                             start_time=stream_start_time,
                                             stop_when_empty=stop_when_empty)

        # Used for BytesIO of the jpeg frame.
        def create_stream(byte_writers):
            return streamer.StreamSaver(stream=stream,
                                        byte_writers=byte_writers,
                                        name=debug_name,
                                        stop_when_empty=stop_when_empty)

        def create_dropbox_writer(_path, _pem_path=None, _file_chunk_size=-1):
            return dropbox_writer.DropboxWriter(full_path=_path,
                                                dropbox_token=self.__dropbox_config['api_token'],
                                                file_chunk_size=_file_chunk_size,
                                                public_pem_path=_pem_path)

        streamers = []
        disk_path = os.path.join(self.__instance_path, 'recordings', path)
        writers = [disk_writer.DiskWriter(disk_path)]
        if isinstance(stream, picamera.PiCameraCircularIO): # Video
            if len(self.__dropbox_config) != 0:
                key_path = None
                if 'public_key_path' in self.__dropbox_config:
                    key_path = self.__dropbox_config['public_key_path']
                
                writers.append(create_dropbox_writer('/'+os.path.join(self.camera.name, path),
                                                     _pem_path=key_path,
                                                     _file_chunk_size=self.__dropbox_config['file_chunk_mb'] * 1024 * 1024))
            streamers.append(create_cam_stream(writers))
        else: # JPEG
            if len(self.__dropbox_config) != 0:
                writers.append(create_dropbox_writer('/'+os.path.join(self.camera.name, path)))
            streamers.append(create_stream(writers))

        list(map(lambda x: x.start(), streamers))
        return streamers

    def run(self):
        
        camera = self.camera
        logger = logging.getLogger(__name__)
        logger.info('Starting main loop.')
        camera.start_recording(self.__stream, format='h264')

        self.__start_time = time.time()

        try:
            was_not_running = True
            while True:
                if not camera.should_monitor:
                    if self.__micro_comm is not None:
                        self.__micro_comm.infrared_running = False
                    was_not_running = True
                    self.wait()
                    continue

                if was_not_running:
                    # Allow the camera a few seconds to initialize.
                    for _ in range(int(INITIALIZATION_TIME / WAIT_TIME)):
                        self.wait()
                    # Reset the base frame after coming online.
                    self.__motion_detector.reset_base_frame()
                    was_not_running = False

                if self.__micro_comm is not None:                        
                    self.__micro_comm.infrared_running = True

                self.wait()
                motion_detected, frame_bytes = self.__motion_detector.detect()
                if motion_detected or camera.should_record:
                    self.wait() # Update the annotation area after the heavy detect() call.

                    self.__motion_detector.reset_base_frame_date()
                    logger.info('Recording triggered.')
                    event_time = time.time()
                    event_date = dt.datetime.now()
                    day_str = event_date.strftime(self.__day_format)
                    time_str = event_date.strftime(self.__time_format)
                    full_dir = os.path.join(day_str, time_str)
                    logger.info(full_dir)

                    # Save the JPG
                    self.save_stream(io.BytesIO(frame_bytes),
                                        path=os.path.join(full_dir, 'trigger.jpg'),
                                        debug_name=time_str + '.jpg',
                                        stop_when_empty=True)
                    self.wait() # Update the annotation area after the heavy save_stream() call.

                    # Save the video
                    video_streamers = self.save_stream(self.__stream,
                                                       path=os.path.join(full_dir, 'video.h264'),
                                                       debug_name=time_str+'.vid')
                    self.wait() # Update the annotation area after the heavy save_stream() call.

                    # Wait for motion to stop
                    last_motion_trigger = time.time()
                    while camera.should_monitor and \
                            time.time() - last_motion_trigger <= self.__padding and \
                            time.time() - event_time <= self.__max_event_time:
                          
                        more_motion, _ = self.__motion_detector.detect()
                        if more_motion:
                            logger.debug('More motion detected!')
                            last_motion_trigger = time.time()
                        for _ in range(int(MOTION_INTERVAL_WHILE_SAVING / WAIT_TIME)):
                            self.wait()

                    # Now that motion is done, stop uploading
                    list(map(lambda x: x.stop(), video_streamers))
                    camera.should_record = False
                    elapsed_time = (dt.datetime.now() - event_date).seconds
                    logger.info('Ending recording. Elapsed time %ds' % elapsed_time)
        except Exception as e:
            logger.exception('An exception occurred: %s' % e)
        finally:
            camera.stop_recording()
            camera.close()
