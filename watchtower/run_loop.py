
from flask import Flask
from threading import Thread
import io
import logging
import datetime as dt
import picamera
import time
from .camera import Servo, SafeCamera
from .motion.motion_detector import MotionDetector
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

        if app.config.get('INFRA_ENABLED') == True:
            self.__ir_controller = self.setup_infrared_controller(app)
        else:
            self.__ir_controller = None

        self.camera = self.setup_camera(app)
        
        motion_config = app.config.get_namespace('MOTION_')
        area = motion_config['max_trigger_area']
        delta = motion_config['pixel_delta_trigger']
        self.__padding = motion_config['recording_padding']
        self.__max_event_time = motion_config['max_event_time']
        self.__motion_detector = MotionDetector(self.camera, delta, area)
        self.__stream = picamera.PiCameraCircularIO(self.camera, seconds=self.__padding)

        self.__start_time = None
        self.__day_format = app.config['DIR_DAY_FORMAT']
        self.__time_format = app.config['DIR_TIME_FORMAT']
        self.__video_date_format = app.config['VIDEO_DATE_FORMAT']
        self.__dropbox_config  = app.config.get_namespace('DROPBOX_')

    @property
    def ir_controller(self):
        return self.__ir_controller

    @property
    def start_time(self):
        return self.__start_time

    def setup_infrared_controller(self, app):
        from .remote.ir_serial import InfraredComm
        infra_config = app.config.get_namespace('INFRA_')
        controller = InfraredComm(on_command=infra_config['on_command'],
                                  off_command=infra_config['off_command'],
                                  port=infra_config['port'],
                                  baudrate=infra_config['baudrate'],
                                  timeout=infra_config['timeout'],
                                  sleep_time=1.0/infra_config['update_hz'])
        controller.start()
        return controller

    def setup_camera(self, app):
        servos = []
        for s in app.config.get('SERVOS'):
            servos.append(Servo(pin=s['BOARD_PIN'],
                                angle_off=s['ANGLE_OFF'],
                                angle_on=s['ANGLE_ON']))
        camera = SafeCamera(name = app.config["CAMERA_NAME"],
                            resolution=tuple(app.config['VIDEO_SIZE']),
                            framerate=app.config['VIDEO_FRAMERATE'],
                            servos=servos)
        camera.rotation = app.config.get('VIDEO_ROTATION')
        camera.annotate_background = picamera.Color('black')
        camera.annotate_text_size = 12
        return camera

    def wait(self):
        """Briefly waits on the camera and updates the annotation on the feed."""

        date_string = dt.datetime.now().strftime(self.__video_date_format)
        self.camera.annotate_text = '{} {}'.format(self.camera.name, date_string)
        if self.ir_controller is not None:
            self.camera.annotate_text = self.camera.annotate_text + ' ' + str(self.ir_controller.room_brightness)
        self.camera.wait_recording(WAIT_TIME)

    def save_stream(self, stream, path, debug_name, stop_when_empty=False):
        """Saves the ``stream`` to disk and optionally Dropbox, if Dropbox
        configurations were supplied in the config file."""

        stream_start_time = max(0, int(time.time() - self.start_time - self.__padding))

        def create_cam_stream(_debug_name, byte_writer):
            return streamer.VideoStreamSaver(stream=stream,
                                        byte_writer=byte_writer,
                                        name=_debug_name,
                                        start_time=stream_start_time,
                                        stop_when_empty=stop_when_empty)

        def create_stream(_debug_name, byte_writer):
            return streamer.StreamSaver(stream=stream,
                                        byte_writer=byte_writer,
                                        name=_debug_name,
                                        stop_when_empty=stop_when_empty)

        def create_dropbox_writer(_path, _pem_path=None):
            return dropbox_writer.DropboxWriter(full_path=_path,
                                                dropbox_token=self.__dropbox_config['token'],
                                                file_chunk_size=self.__dropbox_config['file_chunk_mb'] * 1024 * 1024,
                                                public_pem_path=_pem_path)

        streamers = []
        if isinstance(stream, picamera.PiCameraCircularIO):
            streamers.append(create_cam_stream(debug_name+'.loc', disk_writer.DiskWriter(path)))
            if len(self.__dropbox_config) != 0:
                streamers.append(create_cam_stream(debug_name+'.dbx',
                                                create_dropbox_writer('/'+path,
                                                                        dropbox_config['public_key_path'])))
        else:
            streamers.append(create_stream(debug_name+'.loc', disk_writer.DiskWriter(path)))
            if len(self.__dropbox_config) != 0:
                stream = io.BytesIO(stream.getvalue())  # Create a new stream for Dropbox.
                streamers.append(create_stream(debug_name+'.dbx', create_dropbox_writer('/'+path)))

        list(map(lambda x: x.start(), streamers))
        return streamers

    def run(self):
        
        camera = self.camera
        logger = logging.getLogger(__name__)
        logger.info('Running main loop.')
        camera.start_recording(self.__stream, format='h264')

        self.__start_time = time.time()

        try:
            was_not_running = True
            while True:
                if not camera.should_monitor:
                    if self.ir_controller is not None:
                        self.ir_controller.turn_off()
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

                if self.ir_controller is not None:                        
                    self.ir_controller.turn_on()

                self.wait()
                motion_detected, frame_bytes = self.__motion_detector.detect()
                if motion_detected or camera.should_record:
                    self.__motion_detector.reset_base_frame_date()
                    logger.info('Recording triggered.')
                    event_time = time.time()
                    event_date = dt.datetime.now()
                    day_str = event_date.strftime(self.__day_format)
                    time_str = event_date.strftime(self.__time_format)
                    full_dir = self.camera.name + '/' + day_str + '/' + time_str

                    self.save_stream(io.BytesIO(frame_bytes),
                                        path=full_dir + '/trigger.jpg',
                                        debug_name=time_str + '.jpg',
                                        stop_when_empty=True)
                    video_streamers = self.save_stream(self.__stream,
                                                       path=full_dir+'/video.h264',
                                                       debug_name=time_str+'.vid')

                    # Wait for motion to stop
                    last_motion_trigger = time.time()
                    while camera.should_monitor and time.time() - last_motion_trigger <= self.__padding and \
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
