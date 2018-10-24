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


def init_command_receiver():
    if config['command_port'] is not None:
        remote.CommandReceiver(get_running_callback=get_running,
                               set_running_callback=set_running,
                               port=config['command_port']).start()
    return Lock(), True


def init_camera():
    camera = picamera.PiCamera(resolution=(tuple(config['video_size'])),
                               framerate=config['framerate'])
    camera.rotation = config['rotation']
    camera.annotate_background = picamera.Color('black')
    camera.annotate_text_size = 12
    return camera


def wait(camera):
    """Single point where we record camera data. This also updates the
    annotation on the feed."""

    camera.annotate_text = config['cam_name'] + dt.datetime.now().strftime(config['overlay_date_format'])
    camera.wait_recording(WAIT_TIME)


def save_stream(stream, path, debug_name, stop_when_empty=False):
    """Saves the ``stream`` to disk and optionally Dropbox, if a Dropbox token
     was supplied as a parameter to the program."""

    streamers = [streamer.StreamSaver(stream=stream,
                                      byte_writer=writer.DiskWriter(path),
                                      name=debug_name+'.loc',
                                      stop_when_empty=stop_when_empty)]

    if config['dropbox_token'] is not None:
        dropbox_writer = writer.DropboxWriter(full_path='/' + path,
                                              dropbox_token=config['dropbox_token'])
        streamers.append(streamer.StreamSaver(stream=stream,
                                              byte_writer=dropbox_writer,
                                              name=debug_name+'.dbx',
                                              stop_when_empty=stop_when_empty))
    map(lambda x: x.start(), streamers)
    return streamers


def set_running(r):
    """Thread-safe setter to turn motion detection on and off. Even when off,
    the camera still records to an in-memory buffer."""

    global running
    status_lock.acquire()
    running = r
    status_lock.release()


def get_running():
    status_lock.acquire()
    status = running
    status_lock.release()
    return status


def main():
    camera = init_camera()
    with camera:
        motion_detector = motion.MotionDetector(camera, config['min_delta'], config['min_trigger_area'])
        stream = picamera.PiCameraCircularIO(camera, seconds=config['min_rec_time_after_trigger'])
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

                    event_date = dt.datetime.now()
                    day_str = event_date.strftime(config['day_dir_date_format'])
                    time_str = event_date.strftime(config['time_dir_date_format'])
                    full_dir = config['cam_name'] + '/' + day_str + '/' + time_str

                    save_stream(io.BytesIO(motion_frame_bytes),
                                path=full_dir + '/motion0.jpg',
                                debug_name=time_str + '.jpg0',
                                stop_when_empty=True)
                    video_streamers = save_stream(stream,
                                                  path=full_dir+'/video.h264',
                                                  debug_name=time_str+'.vid')

                    # Capture a minimum amount of video after motion
                    while (dt.datetime.now() - event_date).seconds < config['min_rec_time_after_trigger']:
                        wait(camera)

                    # Wait for motion to stop
                    last_motion_trigger = time.time()
                    motion_count = 0
                    while time.time() - last_motion_trigger <= config['min_rec_time_after_trigger']:
                        more_motion, motion_frame_bytes = motion_detector.detect()
                        if more_motion:
                            logger.debug('More motion detected!')
                            motion_count += 1
                            last_motion_trigger = time.time()
                            save_stream(io.BytesIO(motion_frame_bytes),
                                        path=full_dir + '/motion' + str(motion_count) + '.jpg',
                                        debug_name=time_str + '.jpg' + str(motion_count),
                                        stop_when_empty=True)

                        # Timeout for a second
                        for i in range(int(CONTINUOUS_MOTION_INTERVAL / WAIT_TIME)):
                            wait(camera)

                    # Now that motion is done, stop uploading
                    map(lambda x: x.stop(), video_streamers)
                    elapsed_time = (dt.datetime.now() - event_date).seconds
                    logger.info('Motion stopped; ended recording. Elapsed time %ds' % elapsed_time)
        except Exception as e:
            logger.exception('An exception occurred: %s' % e.message)
        finally:
            camera.stop_recording()
            camera.close()


if __name__ == '__main__':
    config = init_config()
    logger = init_logging()
    status_lock, running = init_command_receiver()
    main()
