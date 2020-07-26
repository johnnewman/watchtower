"""Entry point for the Watchtower Flask app.

This is where the Flask app is created to monitor a Raspberry Pi camera's feed.
All supported API endpoints are defined in this module. One instance of the
RunLoop thread is started when the app is initialized.
"""

from flask import Flask, Response, stream_with_context
import json
import logging.config
import os
import time
from .run_loop import RunLoop
from .streamer.mjpeg_streamer import MJPEGStreamer
from .streamer.writer.socket_writer import ServoSocketWriter
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

    @app.route('/status')
    def status():
        return dict(monitoring=main.camera.should_monitor)

    @app.route('/stop')
    def stop():
        main.camera.should_monitor = False
        hide_camera()
        return status()

    @app.route('/start')
    def start():
        main.camera.should_monitor = True
        expose_camera()
        return status()

    @app.route('/record')
    def record():
        main.camera.should_record = True
        return '', 204

    @app.route('/stream')
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
                                 byte_writer=writer,
                                 name='MJPEG',
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
        if main.micro_comm is not None and main.servo is not None:
            main.micro_comm.set_servo_angle(main.servo.angle_on)
    
    def hide_camera():
        if main.micro_comm is not None and main.servo is not None:
            main.micro_comm.set_servo_angle(main.servo.angle_off)

    return app
