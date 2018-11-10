import argparse
import cam
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
    remote.CommandServer(port=config['server']['server_port'],
                         certfile=config['server']['certfile_path'],
                         keyfile=config['server']['keyfile_path'],
                         api_key=config['server']['api_key'],
                         api_key_header_name=config['server']['api_key_header_name'],
                         camera=camera,
                         mjpeg_rate_cap=config['server']['mjpeg_framerate_cap']).start()


def init_camera():
    camera = cam.SafeCamera(resolution=tuple(config['video_size']),
                            framerate=config['framerate'])
    camera.rotation = config['rotation']
    camera.annotate_background = picamera.Color('black')
    camera.annotate_text_size = 12
    return camera


def wait(camera):
    """Briefly waits on the camera and updates the annotation on the feed."""

    camera.annotate_text = cam_name + dt.datetime.now().strftime(config['formats']['overlay_date_format'])
    camera.wait_recording(WAIT_TIME)


def save_stream(stream, path, debug_name, stop_when_empty=False):
    """Saves the ``stream`` to disk and optionally Dropbox, if a Dropbox token
     was supplied as a parameter to the program."""

    stream_start_time = max(0, int(time.time() - start_time - rec_sec_before_trigger))

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
                                    file_chunk_size=dropbox_chunk_size)

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


def get_camera():
    return camera


def main():
    with camera:
        day_dir_format = config['formats']['day_directory_format']
        time_dir_format = config['formats']['time_directory_format']
        max_event_time = config['motion']['max_event_time']
        rec_sec_after_trigger = config['motion']['rec_sec_after']

        area = config['motion']['min_trigger_area']
        delta = config['motion']['min_pixel_delta_trigger']
        motion_detector = motion.MotionDetector(camera, delta, area)

        stream = picamera.PiCameraCircularIO(camera, seconds=rec_sec_before_trigger)
        camera.start_recording(stream, format='h264')
        logger.info('Initialized.')

        # Allow the camera a few seconds to initialize
        for i in range(int(INITIALIZATION_TIME / WAIT_TIME)):
            wait(camera)

        try:
            while True:
                if not camera.should_monitor:
                    wait(camera)
                    continue

                wait(camera)
                motion_detected, motion_frame_bytes = motion_detector.detect()
                if motion_detected:
                    motion_detector.reset_base_frame_date()
                    logger.info('Motion detected!')
                    event_time = time.time()
                    event_date = dt.datetime.now()
                    day_str = event_date.strftime(day_dir_format)
                    time_str = event_date.strftime(time_dir_format)
                    full_dir = cam_name + '/' + day_str + '/' + time_str

                    save_stream(io.BytesIO(motion_frame_bytes),
                                path=full_dir + '/motion.jpg',
                                debug_name=time_str + '.jpg',
                                stop_when_empty=True)
                    video_streamers = save_stream(stream,
                                                  path=full_dir+'/video.h264',
                                                  debug_name=time_str+'.vid')

                    # Wait for motion to stop
                    last_motion_trigger = time.time()
                    while camera.should_monitor and time.time() - last_motion_trigger <= rec_sec_after_trigger and \
                            time.time() - event_time <= max_event_time:
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
    logger = init_logging()
    config = init_config()
    cam_name = config['cam_name']
    dropbox_token = config['dropbox']['token']
    dropbox_chunk_size = config['dropbox']['file_chunk_megs']
    if dropbox_chunk_size is not None:
        dropbox_chunk_size *= 1024 * 1024
    rec_sec_before_trigger = config['motion']['rec_sec_before']

    camera = init_camera()
    start_time = time.time()
    if config['server']['enabled']:
        init_command_server()
    main()
