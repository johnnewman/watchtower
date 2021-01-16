"""Entry point for the Watchtower Flask app.

This is where the Flask app is created to monitor a Raspberry Pi camera's feed.
All supported API endpoints are defined in this module. One instance of the
RunLoop thread is started when the app is initialized.
"""

from datetime import datetime
from flask import Flask, Response, jsonify, request, stream_with_context, render_template, send_from_directory
import json
import logging.config
import os
import picamera
import time
from .remote.servo import Servo
from .run_loop import RunLoop
from .streamer.mjpeg_streamer import MJPEGStreamer
from .streamer.writer import http_writer
from .util import file_system as fs

__author__ = "John Newman"
__copyright__ = "Copyright 2020, John Newman"
__license__ = "MIT"
__version__ = "1.6.0"
__maintainer__ = "John Newman"
__status__ = "Production"

def setup_logging(app):
    with open(os.environ.get('LOG_CONFIG'), 'r') as log_config_file:
        logging.config.dictConfig(json.load(log_config_file))

def create_app(test_config=None):
    """
    Initializes the Flask app and starts the main RunLoop thread. This is how
    uWSGI starts the program.
    """
    app = Flask(__name__)
    if test_config is None:
        app.config.from_json(os.environ.get('WATCHTOWER_CONFIG'), silent=False)
    else:
        app.config.from_mapping(test_config)
    setup_logging(app)
    main = RunLoop(app)

    add_api_routes(app, main)

    # The web routes are not required and can be omitted. However, they do
    # require the API routes, so to use the web app, you MUST enable the API.
    if 'WEB_APP_ENABLED' in app.config:
        if app.config['WEB_APP_ENABLED'] == True:
            add_web_routes(app, main)
            logging.getLogger(__name__).info('Adding web app routes.')

    main.start()
    return app

def add_api_routes(app, main_loop):
    """
    Adds all of the routes for Watchtower's API.
    """

    day_format = app.config['DIR_DAY_FORMAT']
    time_format = app.config['DIR_TIME_FORMAT']

    @app.route('/api/status')
    def status():
        return dict(monitoring=main_loop.camera.should_monitor)

    @app.route('/api/stop')
    def stop():
        main_loop.camera.should_monitor = False
        hide_camera()
        return status()

    @app.route('/api/start')
    def start():
        main_loop.camera.should_monitor = True
        expose_camera()
        return status()
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def config():
        if request.method == 'POST':
            return main_loop.camera.update_config_params(request.json)
        else:
            return main_loop.camera.config_params()

    @app.route('/api/record')
    def record():
        main_loop.camera.should_record = True
        return '', 204

    @app.route('/api/recordings')
    def recordings():
        """
        GET all recordings in Watchtower.
        """
        recordings = fs.all_recordings(path=os.path.join(app.instance_path, 'recordings'),
                                       day_format=day_format,
                                       time_format=time_format)
        return jsonify(recordings), 200

    @app.route('/api/recordings/<day>', methods=['GET', 'DELETE'])
    def recordings_for_day(day):
        """
        GET or DELETE all recordings for a day.
        """
        if request.method == 'DELETE':
            return delete_recording(day)
        try:
            if datetime.strptime(day, day_format) is not None:
                times = fs.all_recording_times_for_day(path=os.path.join(app.instance_path, 'recordings'),
                                                       day_dirname=day,
                                                       time_format=time_format)
                return jsonify(times), 200
        except ValueError:
            pass
        return '', 422
    
    @app.route('/api/recordings/<path:path>', methods=['DELETE'])
    def delete_recording(path):
        """
        DELETE recording for a specified day and time in /recordings/day/time.
        """
        elements = path.split('/')
        if len(elements) != 1 and len(elements) != 2:
            return '', 422
        try:
            day = elements[0]
            time = elements[1] if len(elements) == 2 else None
            if datetime.strptime(day, day_format) is not None:
                if time is None or datetime.strptime(time, time_format) is not None:
                    successful = fs.delete_recording(path=os.path.join(app.instance_path, 'recordings'),
                                                     day_dirname=day,
                                                     time_dirname=time)
                    if successful:
                        return '', 204
                    return '', 404
        except ValueError:
            pass
        return '', 422

    @app.route('/api/recordings/<path:path>/trigger')
    def video_recording(path):
        """
        GET a trigger jpeg for a day and time.
        """
        return serve_recording('trigger.jpg', path)

    @app.route('/api/recordings/<path:path>/video')
    def recording_video(path):
        """
        GET a recording video for a day and time.
        """
        return serve_recording('video.h264', path)

    def serve_recording(name, path):
        elements = path.split('/')
        if not len(elements) == 2:
            return '', 422
        try:
            day = elements[0]
            time = elements[1]
            if datetime.strptime(day, day_format) is not None:
                if datetime.strptime(time, time_format) is not None:
                    directory = os.path.join(app.instance_path, 'recordings', day, time)
                    return send_from_directory(os.path.abspath(directory),
                                               name,
                                               as_attachment=True,
                                               attachment_filename=('%s;%s;%s' % (day, time, name)))
        except ValueError:
            pass
        return '', 422

    def expose_camera():
        if main_loop.servo is not None:
            main_loop.servo.enable()
    
    def hide_camera():
        if main_loop.servo is not None:
            main_loop.servo.disable()

    @app.route('/api/internal_mjpeg')
    def internal_stream():
        return shared_stream(main_loop)

    @app.route('/api/internal_motion')
    def motion():
        main_loop.camera.motion_detected = True
        return '', 200

def add_web_routes(app, main_loop):
    """
    Adds all of the routes for Watchtower's the web app.
    """

    day_format = app.config['DIR_DAY_FORMAT']
    time_format = app.config['DIR_TIME_FORMAT']

    @app.route('/')
    def index():
        config_params = dict(
            awb_modes=picamera.PiCamera.AWB_MODES,
            exposure_modes=picamera.PiCamera.EXPOSURE_MODES,
            image_effects=picamera.PiCamera.IMAGE_EFFECTS,
            meter_modes=picamera.PiCamera.METER_MODES
        )
        recordings = fs.all_recordings(path=os.path.join(app.instance_path, 'recordings'),
                                       day_format=day_format,
                                       time_format=time_format)
        return render_template('base.html',
                               camera=main_loop.camera,
                               recordings=recordings,
                               config_params=config_params)
    
    @app.route('/mjpeg')
    def stream():
        return shared_stream(main_loop)

def shared_stream(main_loop):
    """
    Starts an MJPEG stream using an HTTPMultipartWriter fed to an instance
    of MJPEGStreamer. A generator is used to continuously block, waiting on
    a signal from the writer when a new frame is ready for output to the
    client.

    An optional encoding=base64 parameter can be supplied to encode the raw
    image data in the response.
    """
    encoding = request.args.get('encoding', type=str)
    fps = 4
    writer = http_writer.HTTPMultipartWriter(use_base64=(encoding == 'base64'))
    streamer = MJPEGStreamer(main_loop.camera,
                            byte_writers=[writer],
                            name='MJPEG',
                            servo=main_loop.servo,
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