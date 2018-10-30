import argparse
import datetime as dt
import io
import json
import logging.config
import motion
import os
import picamera
import remote
import streamer
import streamer.writer as writer
from threading import Lock
import time

WAIT_TIME = 0.1
INITIALIZATION_TIME = 3  # In Seconds
MOTION_INTERVAL_WHILE_SAVING = 1.0  # In Seconds


def init_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--config-file",
                        type=str,
                        default='config/camera_config.json',
                        help='location of the config json file.')
    supplied_args = vars(parser.parse_args())
    with open(supplied_args['config_file'], 'r') as config_file:
        return json.load(config_file)


def init_logging():
    log_dir = 'logs/'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open('config/log_config.json', 'r') as log_config_file:
        logging.config.dictConfig(json.load(log_config_file))
    return logging.getLogger(__name__)


def init_command_server():
    if command_port is not None:
        remote.CommandServer(get_camera_callback=get_camera,
                             get_running_callback=get_running,
                             set_running_callback=set_running,
                             port=command_port).start()
    return Lock(), False


def init_camera():
    camera = picamera.PiCamera(resolution=(video_size),
                               framerate=framerate)
    camera.rotation = rotation
    camera.annotate_background = picamera.Color('black')
    camera.annotate_text_size = 12
    return camera


def wait(camera):
    """Single point where we record camera data. This also updates the
    annotation on the feed."""

    camera.annotate_text = cam_name + dt.datetime.now().strftime(overlay_date_format)
    camera.wait_recording(WAIT_TIME)


def save_stream(stream, path, debug_name, stop_when_empty=False):
    """Saves the ``stream`` to disk and optionally Dropbox, if a Dropbox token
     was supplied as a parameter to the program."""

    stream_start_time = max(0, int(time.time() - start_time - rec_time_before_trigger))

    def create_cam_stream(_debug_name, byte_writer):
        return streamer.CamStreamSaver(stream=stream,
                                       byte_writer=byte_writer,
                                       name=_debug_name,
                                       start_time=stream_start_time,
                                       stop_when_empty=stop_when_empty)

    def create_stream(_debug_name, byte_writer):
        return streamer.StreamSaver(stream=stream,
                                    byte_writer=byte_writer,
                                    name=_debug_name,
                                    stop_when_empty=stop_when_empty)

    def create_dropbox_writer(_path):
        return writer.DropboxWriter(full_path=_path,
                                    dropbox_token=dropbox_token,
                                    file_chunk_size=dropbox_file_chunk_megs)

    streamers = []
    if isinstance(stream, picamera.PiCameraCircularIO):
        streamers.append(create_cam_stream(debug_name+'.loc', writer.DiskWriter(path)))
        if dropbox_token is not None:
            streamers.append(create_cam_stream(debug_name+'.dbx', create_dropbox_writer('/'+path)))
    else:
        streamers.append(create_stream(debug_name+'loc', writer.DiskWriter(path)))
        if dropbox_token is not None:
            streamers.append(create_stream(debug_name+'.dbx', create_dropbox_writer('/'+path)))

    map(lambda x: x.start(), streamers)
    return streamers


def set_running(r):
    """
    Thread-safe setter to turn motion detection on and off. Even when off,
    the camera still records to an in-memory buffer.
    """
    global running
    status_lock.acquire()
    running = r
    status_lock.release()


def get_running():
    status_lock.acquire()
    status = running
    status_lock.release()
    return status


def get_camera():
    return camera


def main():
    with camera:
        motion_detector = motion.MotionDetector(camera, min_delta, min_trigger_area)
        stream = picamera.PiCameraCircularIO(camera, seconds=rec_time_before_trigger)
        camera.start_recording(stream, format='h264')
        logger.info('Initialized.')

        # Allow the camera a few seconds to initialize
        for i in range(int(INITIALIZATION_TIME / WAIT_TIME)):
            wait(camera)

        try:
            while True:
                if not get_running():
                    time.sleep(1)
                    continue

                wait(camera)
                motion_detected, motion_frame_bytes = motion_detector.detect()
                if motion_detected:
                    motion_detector.reset_base_frame_date()
                    logger.info('Motion detected!')
                    event_time = time.time()
                    event_date = dt.datetime.now()
                    day_str = event_date.strftime(day_dir_date_format)
                    time_str = event_date.strftime(time_dir_date_format)
                    full_dir = cam_name + '/' + day_str + '/' + time_str

                    save_stream(io.BytesIO(motion_frame_bytes),
                                path=full_dir + '/motion0.jpg',
                                debug_name=time_str + '.jpg0',
                                stop_when_empty=True)
                    video_streamers = save_stream(stream,
                                                  path=full_dir+'/video.h264',
                                                  debug_name=time_str+'.vid')

                    # Wait for motion to stop
                    last_motion_trigger = time.time()
                    while get_running() and time.time() - last_motion_trigger <= rec_time_after_trigger and \
                            time.time() - event_time <= max_trigger_time:
                        more_motion, motion_frame_bytes = motion_detector.detect()
                        if more_motion:
                            logger.debug('More motion detected!')
                            last_motion_trigger = time.time()
                        for i in range(int(MOTION_INTERVAL_WHILE_SAVING / WAIT_TIME)):
                            wait(camera)

                    # Now that motion is done, stop uploading
                    map(lambda x: x.stop(), video_streamers)
                    elapsed_time = (dt.datetime.now() - event_date).seconds
                    logger.info('Ending recording. Elapsed time %ds' % elapsed_time)
        except Exception as e:
            logger.exception('An exception occurred: %s' % e.message)
        finally:
            camera.stop_recording()
            camera.close()


if __name__ == '__main__':
    config = init_config()

    cam_name = config['cam_name']
    command_port = config['command_port']
    day_dir_date_format = config['day_dir_date_format']
    dropbox_token = config['dropbox_token']
    framerate = config['framerate']
    max_trigger_time = config['max_trigger_time']
    dropbox_file_chunk_megs = config['dropbox_file_chunk_megs']
    if dropbox_file_chunk_megs is not None:
        dropbox_file_chunk_megs *= 1024*1024
    min_delta = config['min_delta']
    min_trigger_area = config['min_trigger_area']
    overlay_date_format = config['overlay_date_format']
    rec_time_after_trigger = config['rec_time_after_trigger']
    rec_time_before_trigger = config['rec_time_before_trigger']
    rotation = config['rotation']
    time_dir_date_format = config['time_dir_date_format']
    video_size = tuple(config['video_size'])

    logger = init_logging()
    status_lock, running = init_command_server()
    start_time = time.time()
    camera = init_camera()
    main()
