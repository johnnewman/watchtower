"""Entry point for the Watchtower Flask app.

This is where the Flask app is created to monitor a Raspberry Pi camera's feed.
All supported API endpoints are defined in this module. One instance of the
RunLoop thread is started when the app is initialized.
"""

from flask import Flask, Response, request, stream_with_context
import json
import logging.config
import os
import time
from .remote.servo import Servo
from .run_loop import RunLoop
from .streamer.mjpeg_streamer import MJPEGStreamer
from .streamer.writer import http_writer

__author__ = "John Newman"
__copyright__ = "Copyright 2020, John Newman"
__license__ = "MIT"
__version__ = "1.1.0"
__maintainer__ = "John Newman"
__status__ = "Production"

def setup_logging(app):
    filename = os.path.join(app.instance_path, 'log_config.json')
    with open(filename, 'r') as log_config_file:
        logging.config.dictConfig(json.load(log_config_file))
    return logging.getLogger(__name__)

def create_app(test_config=None):
    """
    Initializes the Flask app and starts the main RunLoop thread. This is how
    uWSGI starts the program.
    """
    app = Flask(__name__, instance_relative_config=True)
    if test_config is None:
        app.config.from_json('watchtower_config.json', silent=False)
    else:
        app.config.from_mapping(test_config)
    
    setup_logging(app)
    main = RunLoop(app)
    main.start()

    @app.route('/')
    def index():
        camera_path = request.url_root.rsplit('/', 2)[-2]
        print('Camera path %s' %  camera_path)
        config_params = dict(
            awb_modes=picamera.PiCamera.AWB_MODES,
            exposure_modes=picamera.PiCamera.EXPOSURE_MODES,
            image_effects=picamera.PiCamera.IMAGE_EFFECTS,
            meter_modes=picamera.PiCamera.METER_MODES
        )

        return render_template('base.html',
                               camera=main.camera,
                               api_path=camera_path,
                               config_params=config_params)

    @app.route('/api/status')
    def status():
        return dict(monitoring=main.camera.should_monitor)

    @app.route('/api/stop')
    def stop():
        main.camera.should_monitor = False
        hide_camera()
        return status()

    @app.route('/api/start')
    def start():
        main.camera.should_monitor = True
        expose_camera()
        return status()

    @app.route('/api/record')
    def record():
        main.camera.should_record = True
        return '', 204

    @app.route('/api/config', methods=['GET', 'POST'])
    def config():
        if request.method == 'POST':
            return main.camera.update_config_params(request.json)
        else:
            return main.camera.config_params()

    @app.route('/mjpeg')
    def stream():
        """
        Starts an MJPEG stream using an HTTPMultipartWriter fed to an instance
        of MJPEGStreamer. A generator is used to continuously block, waiting on
        a signal from the writer when a new frame is ready for output to the
        client.
        """
        fps = 0.5
        writer = http_writer.HTTPMultipartWriter()
        streamer = MJPEGStreamer(main.camera,
                                 byte_writers=[writer],
                                 name='MJPEG',
                                 servo=main.servo,
                                 rate=fps)
        streamer.start()

        @stream_with_context
        def generate():
            try:
                while True:
                    yield(writer.blocking_read())
            except:
                streamer.stop()

        mimetype = 'multipart/x-mixed-replace; boundary=' + http_writer.MULTIPART_BOUNDARY
        return Response(generate(), mimetype=mimetype)

    def expose_camera():
        if main.servo is not None:
            main.servo.enable()
    
    def hide_camera():
        if main.servo is not None:
            main.servo.disable()

    return app
