import picamera
import argparse
import datetime as dt
import time
import io
import motion
from streamer import StreamSaver as StreamSaver
from streamer.writer import DiskWriter as DiskWriter, DropboxWriter as DropboxWriter

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--min-area", type=int, default=2000, help="minimum area to trigger motion")
parser.add_argument("-W", "--video-width", type=int, default=1280, help="video capture width")
parser.add_argument("-H", "--video-height", type=int, default=720, help="video capture height")
parser.add_argument("-t", "--min-delta", type=int, default=50, help="minimum delta gray value to threshold")
parser.add_argument("-c", "--cam-name", type=str, default='Cam', help="name of the camera")
parser.add_argument("-m", "--min_motion_time", type=int, default=8, help="minimum time to capture motion")
parser.add_argument("-T", "--dropbox_token", type=str, help="token for Dropbox")
supplied_args = vars(parser.parse_args())


def wait(camera):
    camera.annotate_text = supplied_args["cam_name"] + dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    camera.wait_recording(0.2)


def init_camera():
    camera = picamera.PiCamera()
    camera.rotation = 180
    camera.framerate = 15
    camera.resolution = (supplied_args["video_width"], supplied_args["video_height"])
    camera.annotate_background = picamera.Color('black')
    camera.annotate_text_size = 12
    return camera


def save_jpeg_bytes(jpeg_bytes, path, debug_name):
    local_jpg_writer = DiskWriter.DiskWriter(full_path=path)
    StreamSaver.StreamSaver(stream=io.BytesIO(jpeg_bytes),
                            byte_writer=local_jpg_writer,
                            name=debug_name + '-LOCAL_JPG',
                            stop_when_empty=True).start()

    if supplied_args["dropbox_token"] is not None:
        cloud_jpg_writer = DropboxWriter.DropboxWriter(full_path='/' + path,
                                                       dropbox_token=supplied_args["dropbox_token"])
        StreamSaver.StreamSaver(stream=io.BytesIO(jpeg_bytes),
                                byte_writer=cloud_jpg_writer,
                                name=debug_name + '-CLOUD_JPG',
                                stop_when_empty=True).start()


def save_video(stream, path, debug_name):
    local_vid_writer = DiskWriter.DiskWriter(full_path=path)
    local_vid_streamer = StreamSaver.StreamSaver(stream=stream,
                                                 byte_writer=local_vid_writer,
                                                 name=debug_name + '-LOCAL_VID')
    local_vid_streamer.start()
    streamers = [local_vid_streamer]

    if supplied_args["dropbox_token"] is not None:
        cloud_vid_writer = DropboxWriter.DropboxWriter(full_path='/' + path,
                                                       dropbox_token=supplied_args["dropbox_token"])
        cloud_vid_streamer = StreamSaver.StreamSaver(stream=stream,
                                                     byte_writer=cloud_vid_writer,
                                                     name=debug_name + '-CLOUD_VID')
        cloud_vid_streamer.start()
        streamers.append(cloud_vid_streamer)

    return streamers


def main():
    camera = init_camera()
    with camera:
        motion_detector = motion.MotionDetector(camera, supplied_args['min_delta'], supplied_args['min_area'])
        stream = picamera.PiCameraCircularIO(camera, seconds=supplied_args['min_motion_time'])
        camera.start_recording(stream, format='h264')

        # Allow the camera time to initialize
        camera.wait_recording(1)

        try:
            while True:
                wait(camera)
                motion_detected, motion_frame_bytes = motion_detector.detect()
                if motion_detected:
                    motion_detector.reset_base_frame_date()
                    print('[%s] Motion detected! ' % supplied_args["cam_name"])

                    event_date = dt.datetime.now()
                    day_dir = event_date.strftime('%Y-%m-%d')
                    time_dir = event_date.strftime('%H.%M.%S')
                    full_dir = supplied_args["cam_name"] + '/' + day_dir + '/' + time_dir

                    video_streamers = save_video(stream, path=full_dir + '/video.h264', debug_name=full_dir)
                    save_jpeg_bytes(motion_frame_bytes, path=full_dir + '/motion.jpg', debug_name=full_dir)

                    # Capture a minimum amount of video after motion
                    while (dt.datetime.now() - event_date).seconds < supplied_args['min_motion_time']:
                        wait(camera)

                    # Wait for motion to stop
                    last_motion_check = time.time()
                    motion_count = 0
                    while motion_detected:
                        if time.time() - last_motion_check >= 1:  # Check for new motion every second
                            motion_detected, motion_frame_bytes = motion_detector.detect()
                            if motion_detected:
                                motion_count += 1
                                save_jpeg_bytes(motion_frame_bytes,
                                                path=full_dir + '/' + str(motion_count) + 'motion.jpg',
                                                debug_name=full_dir)
                            last_motion_check = time.time()
                        wait(camera)

                    # Now that motion is done, stop uploading
                    map(lambda x: x.stop(), video_streamers)
                    elapsed_time = (dt.datetime.now() - event_date).seconds
                    print('>>>> Motion stopped; ended recording. Elapsed time %ds' % elapsed_time)
        finally:
            camera.stop_recording()


main()
