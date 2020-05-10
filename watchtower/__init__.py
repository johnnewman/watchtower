from flask import Flask, Response, stream_with_context
import json
import logging.config
import os
import time
from .run_loop import RunLoop
from .streamer.mjpeg_streamer import MJPEGStreamer
from .streamer.writer.socket_writer import ServoSocketWriter
from .streamer.writer import http_writer


def setup_logging(app):
    #TODO CLEANUP THE LOGGING
    # log_dir = 'logs/'
    # if not os.path.exists(log_dir):
    #     os.makedirs(log_dir)
    with open(app.instance_path + '/log_config.json', 'r') as log_config_file:
        logging.config.dictConfig(json.load(log_config_file))
    return logging.getLogger(__name__)

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    if test_config is None:
        app.config.from_json('watchtower_config.json', silent=False)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    setup_logging(app)
    main = RunLoop(app)
    main.start()

    @app.route('/status')
    def status():
        return dict(running=main.camera.should_monitor)

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

    @app.route('/stream')
    def stream():
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
        for servo in main.camera.servos:
            ServoSocketWriter(servo.pin).send_angle(servo.angle_on)
    
    def hide_camera():
        for servo in main.camera.servos:
            ServoSocketWriter(servo.pin).send_angle(servo.angle_off)

    return app
