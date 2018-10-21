import picamera
import argparse
import datetime as dt
import time
import io
import motion
import streamer
import streamer.writer as writer
import logging.config
import os
import json
from threading import Lock
import remote


def init_camera():
    camera = picamera.PiCamera()
    camera.rotation = 180
    camera.framerate = 15
    camera.resolution = (supplied_args["video_width"], supplied_args["video_height"])
    camera.annotate_background = picamera.Color('black')
    camera.annotate_text_size = 12
    return camera


def init_logging():
    log_dir = 'logs/'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open('logConfig.json', 'r') as config_file:
        logging.config.dictConfig(json.load(config_file))
    return logging.getLogger(__name__)


def init_command_receiver():
    if supplied_args['command_port'] is not None:
        remote.CommandReceiver(set_running_callback=set_running,
                               get_running_callback=get_running,
                               port=supplied_args['command_port']).start()
    return Lock(), True


def wait(camera):
    """Single point where we record camera data. This also updates the
    annotation on the feed."""

    camera.annotate_text = supplied_args["cam_name"] + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    camera.wait_recording(0.2)


def save_stream(stream, path, debug_name, stop_when_empty=False):
    """Saves the ``stream`` to disk and optionally Dropbox, if a Dropbox token
     was supplied as a parameter to the program."""

    streamers = [streamer.StreamSaver(stream=stream,
                                      byte_writer=writer.DiskWriter(path),
                                      name=debug_name,
                                      stop_when_empty=stop_when_empty)]

    if supplied_args["dropbox_token"] is not None:
        dropbox_writer = writer.DropboxWriter(full_path='/' + path,
                                              dropbox_token=supplied_args["dropbox_token"])
        streamers.append(streamer.StreamSaver(stream=stream,
                                              byte_writer=dropbox_writer,
                                              name=debug_name,
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
        min_capture_time = supplied_args['min_capture_time']
        motion_detector = motion.MotionDetector(camera, supplied_args['min_delta'], supplied_args['min_area'])
        stream = picamera.PiCameraCircularIO(camera, seconds=min_capture_time)
        camera.start_recording(stream, format='h264')
        logger.info('Initialized.')

        # Allow the camera time to initialize
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
                    day_str = event_date.strftime('%Y-%m-%d')
                    time_str = event_date.strftime('%H.%M.%S')
                    full_dir = supplied_args["cam_name"] + '/' + day_str + '/' + time_str

                    save_stream(io.BytesIO(motion_frame_bytes),
                                path=full_dir + '/motion.jpg',
                                debug_name=time_str + '.jpg',
                                stop_when_empty=True)
                    video_streamers = save_stream(stream,
                                                  path=full_dir+'/video.h264',
                                                  debug_name=time_str+'.vid')

                    # Capture a minimum amount of video after motion
                    while (dt.datetime.now() - event_date).seconds < min_capture_time:
                        wait(camera)

                    # Wait for motion to stop
                    last_motion_check = time.time()
                    motion_count = 0
                    while motion_detected:
                        if time.time() - last_motion_check >= min_capture_time:
                            motion_detected, motion_frame_bytes = motion_detector.detect()
                            if motion_detected:
                                logger.debug('More motion detected!')
                                motion_count += 1
                                save_stream(io.BytesIO(motion_frame_bytes),
                                            path=full_dir + '/' + str(motion_count) + 'motion.jpg',
                                            debug_name=time_str + '.jpg',
                                            stop_when_empty=True)
                            last_motion_check = time.time()
                        wait(camera)

                    # Now that motion is done, stop uploading
                    map(lambda x: x.stop(), video_streamers)
                    elapsed_time = (dt.datetime.now() - event_date).seconds
                    logger.info('Motion stopped; ended recording. Elapsed time %ds' % elapsed_time)
        except Exception as e:
            logger.exception('An exception occurred: %s' % e.message)
        finally:
            camera.stop_recording()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--min-area", type=int, default=.005, help="minimum percent of video for motion")
    parser.add_argument("-W", "--video-width", type=int, default=1280, help="video capture width")
    parser.add_argument("-H", "--video-height", type=int, default=720, help="video capture height")
    parser.add_argument("-t", "--min-delta", type=int, default=50, help="minimum delta gray value to threshold")
    parser.add_argument("-c", "--cam-name", type=str, default='PySecCam', help="name of the camera")
    parser.add_argument("-m", "--min-capture-time", type=int, default=8, help="minimum time to capture motion")
    parser.add_argument("-T", "--dropbox-token", type=str, help="token for Dropbox")
    parser.add_argument("-p", "--command-port", type=int, help="port to listen for commands")
    supplied_args = vars(parser.parse_args())

    logger = init_logging()
    status_lock, running = init_command_receiver()
    main()
