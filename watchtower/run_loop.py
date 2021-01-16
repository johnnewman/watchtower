
from flask import Flask
from threading import Thread, Lock
import datetime as dt
import io
import logging
import os
import picamera
import time
from .camera import SafeCamera
from .recorder import Recorder, Destination
from .recorder.mjpeg import MJPEGRecorder
from .remote import micro
from .remote.servo import Servo
from .util.shutdown import TerminableThread

WAIT_TIME = 0.1
INITIALIZATION_TIME = 10  # In Seconds
MOTION_INTERVAL_WHILE_SAVING = 1.0  # In Seconds


class RunLoop(TerminableThread):
    """
    This is the central threaded class for Watchtower that is started when the
    Flask app is initialized. It starts a continuous camera stream and waits
    for motion to be detected. Once motion is detected, the triggered frame
    and associated video are saved to disk. The same files can be encrytped and
    sent to Dropbox when configured to do so in the watchtower_config file.
    """

    def __init__(self, app):
        super(RunLoop, self).__init__()

        if int(os.environ['SERIAL_ENABLED']):
            self.setup_microcontroller_comm(app)
        else:
            self.servo = None
            
        self.__padding = app.config['RECORDING_PADDING']
        self.__max_event_time = app.config['MAX_EVENT_TIME']
        self.__instance_path = app.instance_path
        self.__recorders, self.camera = self.setup_destinations(app)
        self.__start_time = None
        self.__day_format = app.config['DIR_DAY_FORMAT']
        self.__time_format = app.config['DIR_TIME_FORMAT']
        self.__video_date_format = app.config['VIDEO_DATE_FORMAT']

    @property
    def servo(self) -> Servo:
        return self.__servo

    @servo.setter
    def servo(self, value):
        self.__servo = value

    def setup_microcontroller_comm(self, app):
        controller_config = app.config.get_namespace('SERVO_')
        angle_on = controller_config['angle_on']
        angle_off = controller_config['angle_off']
        if angle_on is not None and angle_off is not None:
            self.servo = Servo(angle_on, angle_off)

    def setup_destinations(self, app):
        """
        Parses all destinations out of the app's config data. The camera will
        also be initialized using the largest resolution from all destinations.
        """

        sizes = {}
        def add_destination(options, destination):
            """
            Adds the destination to the sizes dictionary with the key being the
            resolution. Multiple destinations can share the same resolution.
            """
            size_tuple = tuple(options['size'])
            if size_tuple not in sizes:
                sizes[size_tuple] = []
            sizes[size_tuple].append(destination)

        destinations = app.config.get('DESTINATIONS')
        if destinations is None:
            logging.getLogger(__name__).error('DESTINATIONS key does not exist in config file.')
            raise Exception('Invalid config file')
        
        if 'disk' in destinations:
            options = destinations['disk']
            disk_dest = Destination.disk
            disk_dest.instance_path = self.__instance_path
            add_destination(options, disk_dest)
        if 'dropbox' in destinations:
            options = destinations['dropbox']
            dropbox_dest = Destination.dropbox
            dropbox_dest.token = options['token']
            if 'public_key_path' in options:
                dropbox_dest.pem_path = options['public_key_path']
            dropbox_dest.file_chunk_size = options['file_chunk_kb']*1024
            add_destination(options, dropbox_dest)
        # Future destinations can be set up here.
        
        # Sort with the biggest resolution first.
        sorted_sizes = sorted(sizes.keys(), key=lambda size: size[0], reverse=True)
        splitter_port = 1
        recorders = []
        camera = None
        for size in sorted_sizes:
            logging.getLogger(__name__).info('Creating recorder at %s with splitter port %d.' % (sizes[size], splitter_port))
            resize_resolution = size
            if size == sorted_sizes[0]:
                # The camera's resolution will be set to the largest size. It
                # will use splitter port 1. 
                camera = self.setup_camera(app, size)
                # The largest recorder will not resize the resolution because
                # it will match the camera resolution.
                resize_resolution = None

            recorders.append(
                Recorder(
                    camera=camera,
                    padding_sec=self.__padding,
                    destinations=sizes[size],
                    splitter_port=splitter_port,
                    resize_resolution=resize_resolution
                )
            )
            splitter_port += 1

        # Always create an MJPEG recorder, regardless of user settings.
        mjpeg_port = 0
        mjpeg_size = tuple(app.config['MJPEG_SIZE'])
        logging.getLogger(__name__).info('Creating mjpeg recorder at %s with splitter port %d.' % (mjpeg_size, mjpeg_port))
        recorders.append(
            MJPEGRecorder(
                camera=camera,
                splitter_port=mjpeg_port,
                resize_resolution=mjpeg_size
            )
        )
        return recorders, camera

    def setup_camera(self, app, resolution):
        camera = SafeCamera(name = app.config["CAMERA_NAME"],
                            resolution=resolution,
                            framerate=app.config['VIDEO_FRAMERATE'],
                            config_path=os.path.join(app.instance_path, 'camera_config.json'))
        camera.rotation = app.config.get('VIDEO_ROTATION')
        camera.annotate_background = picamera.Color('black')
        camera.annotate_text_size = 18
        return camera

    def wait(self):
        """
        Briefly waits on each of the camera's splitter ports and updates the
        annotation on the feed.
        """
        date_string = dt.datetime.now().strftime(self.__video_date_format)
        text = '{} | {}'.format(self.camera.name, date_string)

        # Only show brightness if the microcontroller is on and we're monitoring.
        if int(os.environ['SERIAL_ENABLED']) and self.camera.should_monitor:
            text = text + ' | Brightness: ' + micro.get_brightness()

        self.camera.annotate_text = text
        for recorder in self.__recorders:
            self.camera.wait_recording(
                timeout=WAIT_TIME/len(self.__recorders),
                splitter_port=recorder.splitter_port)

    def run(self):
        camera = self.camera
        logger = logging.getLogger(__name__)
        logger.info('Starting main loop.')
        for recorder in self.__recorders:
            recorder.start_recording()
        
        self.__start_time = time.time()
        try:
            was_not_running = True
            while self.should_run:
                if not camera.should_monitor:
                    if not was_not_running:
                        micro.set_running(False)
                    was_not_running = True
                    self.wait()
                    continue

                if was_not_running:
                    # Start microcontroller.
                    micro.set_running(True)
                    # Allow the camera a few seconds to initialize.
                    for _ in range(int(INITIALIZATION_TIME / WAIT_TIME)):
                        self.wait()
                    # Reset the motion flag after coming online.
                    self.camera.motion_detected = False
                    
                    was_not_running = False

                self.wait()
                if camera.should_monitor and (camera.motion_detected or camera.should_record):
                    logger.info('Recording triggered.')
                    event_time = time.time()
                    event_date = dt.datetime.now()
                    day_str = event_date.strftime(self.__day_format)
                    time_str = event_date.strftime(self.__time_format)
                    full_dir = os.path.join(day_str, time_str)
                    logger.info(full_dir)
                    camera.motion_detected = False

                    start_frame_time = max(0, int(time.time() - self.__start_time - self.__padding))
                    for recorder in self.__recorders:
                        recorder.persist(
                            directory=full_dir,
                            start_time=start_frame_time,
                            frame=io.BytesIO(camera.jpeg_data)
                        )
                    self.wait() # Update the annotation area after the heavy persist() call.

                    # Wait for motion to stop
                    last_motion_trigger = time.time()
                    while camera.should_monitor and \
                            time.time() - last_motion_trigger <= self.__padding and \
                            time.time() - event_time <= self.__max_event_time:
                        
                        if camera.motion_detected:
                            logger.debug('More motion detected!')
                            last_motion_trigger = time.time()
                            camera.motion_detected = False
                        for _ in range(int(MOTION_INTERVAL_WHILE_SAVING / WAIT_TIME)):
                            self.wait()

                    # Now that motion is done, stop uploading
                    for recorder in self.__recorders:
                        recorder.stop_persisting()
                    camera.should_record = False
                    elapsed_time = (dt.datetime.now() - event_date).seconds
                    logger.info('Ending recording. Elapsed time %ds' % elapsed_time)
        except Exception as e:
            logger.exception('An exception occurred: %s' % e)
        finally:
            try:
                logger.info('Closing camera.')
                for recorder in self.__recorders:
                    recorder.stop_recording()
                camera.close()
            except Exception as e:
                pass
        logger.debug('Thread stopped.')
