import json
import logging
import os
import picamera
from threading import Lock


class SafeCamera (picamera.PiCamera):
    """
    A camera class that provides a safe mechanism for multiple threads to
    capture an image using ``safe_capture`` or get/set the monitoring status.
    """

    def __init__(self, name, resolution, framerate, config_path):
        super(SafeCamera, self).__init__(resolution=resolution, framerate=framerate)
        self.__should_monitor = True
        self.__should_record = False
        self.__lock = Lock()
        self.__name = name
        self.__config_path = config_path
        self.load_config()
        
    @property
    def name(self):
        return self.__name

    @property
    def should_record(self):
        self.__lock.acquire()
        should_record = self.__should_record
        self.__lock.release()
        return should_record

    @should_record.setter
    def should_record(self, value):
        self.__lock.acquire()
        self.__should_record = value
        self.__lock.release()

    @property
    def should_monitor(self):
        self.__lock.acquire()
        should_monitor = self.__should_monitor
        self.__lock.release()
        return should_monitor

    @should_monitor.setter
    def should_monitor(self, value):
        self.__lock.acquire()
        self.__should_monitor = value
        self.__lock.release()

    def safe_capture(self, output, format='jpeg', use_video_port=True, downscale_factor=None):
        self.__lock.acquire()
        new_resolution = None
        if downscale_factor is not None:
            new_resolution = tuple(int(i * downscale_factor) for i in self.resolution)
        self.capture(output,
                     format=format,
                     use_video_port=use_video_port,
                     resize=new_resolution)
        self.__lock.release()

    def load_config(self):
        if os.path.exists(self.__config_path):
            try:
                with open(self.__config_path, 'r') as f:
                    config = json.load(f)
                    self.update_config_params(config)
            except Exception as e:
                logging.getLogger(__name__).exception('Exception reading %s file. Purging the file! Exception: %s' % (self.__config_path, e))
                try:
                    os.remove(self.__config_path)
                except Exception as e2:
                    pass
        else:
            logging.getLogger(__name__).info('\"%s\" file does not exist.' % self.__config_path)

    def save_config(self):
        params = self.config_params()
        try:
            with open(self.__config_path, 'w') as f:
                f.write(json.dumps(params, indent=2, sort_keys=True))
        except Exception as e:
                logging.getLogger(__name__).exception('Exception saving %s file: %s' % (self.__config_path, e))

    def update_config_params(self, params):
        self.should_monitor = False
        if 'awb_mode' in params:
            awb_mode = params['awb_mode']
            if awb_mode in picamera.PiCamera.AWB_MODES:
                self.awb_mode = awb_mode
        if 'brightness' in params:
            self.brightness = int(params['brightness'])
        if 'contrast' in params:
            self.contrast = int(params['contrast'])
        if 'exposure_compensation' in params:
            self.exposure_compensation = int(params['exposure_compensation'])
        if 'exposure_mode' in params:
            exposure_mode = params['exposure_mode']
            if exposure_mode in picamera.PiCamera.EXPOSURE_MODES:
                self.exposure_mode = exposure_mode
        if 'image_effect' in params:
            image_effect = params['image_effect']
            if image_effect in picamera.PiCamera.IMAGE_EFFECTS:
                self.image_effect = image_effect
        if 'iso' in params:
            self.iso = int(params['iso'])
        if 'meter_mode' in params:
            meter_mode = params['meter_mode']
            if meter_mode in picamera.PiCamera.METER_MODES:
                self.meter_mode = meter_mode
        if 'rotation' in params:
            self.rotation = int(params['rotation'])
        if 'saturation' in params:
            self.saturation = int(params['saturation'])
        if 'sharpness' in params:
            self.sharpness = int(params['sharpness'])
        if 'video_denoise' in params:
            self.video_denoise = bool(params['video_denoise'])
        
        self.save_config()
        self.should_monitor = True
        return self.config_params()
        
    def config_params(self):
        return dict(
            awb_mode=self.awb_mode,
            brightness=self.brightness,
            contrast=self.contrast,
            exposure_compensation=self.exposure_compensation,
            exposure_mode=self.exposure_mode,
            image_effect=self.image_effect,
            iso=self.iso,
            meter_mode=self.meter_mode,
            rotation=self.rotation,
            saturation=self.saturation,
            sharpness=self.sharpness,
            video_denoise=self.video_denoise
        )
