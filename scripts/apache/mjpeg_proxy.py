#!/usr/bin/python

import cgi
import cgi_common as cgic
import re
import socket
import ssl
import sys
import time


READ_CHUNK_SIZE = 4096
NO_DATA_SLEEP_TIME = 0.1


def strip_status_code(buf):
    """
    Used to remove the HTTP status code returned from the HTTP MJPEG streamer.
    Since this is a CGI script, the host server will handle the status code.
    If the MJPEG streamer did not return a 200, this will throw an exception.
    :param buf: The buffer to search.
    :return: A tuple with a flag indicating if the string was removed and the
    new buffer.
    """
    result = re.match('^.+ (?P<status>\d+) .+\r\n', buf)
    if result:
        if int(result.group('status')) == 200:
            return True, buf[result.end():]
        else:
            raise RuntimeError('Bad status code from MJPEG streamer. Aborting')
    return False, buf


def send_next_chunk(buf):
    """
    Finds the next Content-Length key and sends the next content chunk to the
    client, assuming the buffer fully contains the content length.
    :param buf: The buffer to search.
    :return: The buffer with any leading read portion removed.
    """
    result = re.search('\r\nContent-Length: (?P<length>\d+)\r\n\r\n', buf)
    if result:
        end_index = result.end() + int(result.group('length'))
        if len(buf) >= end_index:
            cgic.std(buf[:end_index])
            sys.stdout.flush()
            return buf[end_index:]
    return buf


def extract_fps():
    """
    Parses the FPS field. Uses the config file as a backup in case of errors.
    :return: The FPS.
    """
    fps = cgi.FieldStorage().getvalue('fps', default=float(cgic.controller.camera.default_mjpeg_fps))
    try:
        fps = float(fps)
    except Exception:
        cgic.err('Exception turning FPS into float. Falling back to default.')
        fps = float(cgic.controller.camera.default_mjpeg_fps)
    return fps


def stream_camera():
    """
    Creates a socket connection to the camera address and port defined in the
    config file. Uses the API header field defined in the config file. Reads
    the data from this server and proxy's it to the client in chunks.
    """
    conn = None
    fps = 1.0
    try:
        fps = extract_fps()
        camera = cgic.controller.camera
        conn = ssl.wrap_socket(socket.socket(socket.AF_INET),
                               ca_certs=camera.cert_location,
                               cert_reqs=ssl.CERT_REQUIRED)
        conn.connect((camera.network_address, camera.port))
        conn.send('GET /stream?fps={} HTTP/1.1\r\n'.format(str(fps)) +
                  '{}: {}\r\n\r\n'.format(camera.api_key_header_name, camera.api_key))

    except Exception as e:
        cgic.err('Exception connecting to socket.', repr(e), e.message)
        cgic.stop_with_error('Failed to load stream.')

    try:
        buf = ''
        stripped_code = False
        last_rx_time = time.time()
        byte_count = 0
        while time.time() - last_rx_time < 1.0/fps + 1:
            received_data = conn.recv(READ_CHUNK_SIZE)
            if len(received_data) > 0:
                byte_count += len(received_data)
                last_rx_time = time.time()
                buf += received_data
                if not stripped_code:
                    stripped_code, buf = strip_status_code(buf)
                else:
                    buf = send_next_chunk(buf)
            else:
                time.sleep(NO_DATA_SLEEP_TIME)

        if byte_count == 0:
            raise RuntimeError('No data was read from the stream.')

    except Exception as e:
        cgic.err('Exception reading from socket.', repr(e), e.message)
        cgic.stop_with_error('Failed while reading from stream.')


if cgic.verify_api_key():
    stream_camera()

