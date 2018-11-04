#!/usr/bin/python

from __future__ import print_function
import cgi
import datetime
import json
import os
import re
import socket
import ssl
import sys
import time


FILE_NAME = 'server_proxy.py'
CONF_LOCATION = '/etc/piseccam/proxy_config.json'
READ_CHUNK_SIZE = 4096
NO_DATA_SLEEP_TIME = 0.1


def print_std(*args):
    """
    Writes ``args`` back to the client.
    """
    print(*args, sep=' ', end='', file=sys.stdout)


def print_err(*args):
    """
    Sends ``args`` to the server's error logs.
    """
    print('[{}] [{}]'.format(str(datetime.datetime.now()), FILE_NAME), *args, sep=' ', end='\n', file=sys.stderr)


def stop_with_error(error_string, code=500, code_tile='Internal Server Error'):
    """
    Sends the error code to the client. Wraps the ``error_string`` in a JSON
    object. Stops executing the CGI script.
    """
    print_std('Status: {} {}\r\n'.format(str(code), code_tile))
    print_std('Content-Type: application/json\r\n\r\n')
    print_std(json.dumps(dict(error_message=error_string)))
    sys.exit()


def parse_api_key():
    """
    Searches all headers for the the api key defined in the config json.
    :return: The header value or None if nothing was found.
    """
    for header_name, header_value in os.environ.iteritems():
        if header_name == config_json['api_key_header_name']:
            return header_value
    return None


def strip_status_code(buf):
    """
    Used to remove the HTTP status code returned from the MJPEG streamer. Since
    this is a CGI script, the host server will not like this being sent to the
    client.
    :param buf: The buffer to search.
    :return: A tuple with a flag indicating if the string was removed and the
             new buffer.
    """
    status_code_str = 'HTTP/1.1 200 OK\r\n'
    if buf.startswith(status_code_str):
        return True, buf[len(status_code_str):]
    return False, buf


def find_boundary(buf):
    """
    Performs a search of the supplied buffer looking for the boundary key. This
    safely searches for the entire line, including trailing newlines, to ensure
    that the boundary string was loaded into the buffer in full.
    :param buf: The buffer to search.
    :return: The boundary string or None if it wasn't found.
    """
    result = re.search('Content-Type.*boundary=(?P<boundary>\w+)\r\n', buf)
    if result:
        return result.group('boundary')
    return None


def send_to_boundary(buf, boundary):
    """
    Looks for the next boundary in the supplied buffer. If one is found, the
    chunk of the buffer up to the found boundary is sent to the client.
    :param buf: The buffer to search.
    :param boundary: The boundary string.
    :return: The buffer with any leading read portion removed.
    """
    boundary = '--{}\r\n'.format(boundary)
    index = buf.find(boundary, min(len(boundary), len(buf)))
    if index > -1:
        print_std(buf[:index])
        sys.stdout.flush()
        return buf[index:]
    return buf


def extract_fps():
    fps = cgi.FieldStorage().getvalue('fps', default=float(config_json['camera']['default_fps']))
    try:
        fps = float(fps)
    except Exception:
        print_err('Exception turning FPS into float. Falling back to config file default.')
        fps = float(config_json['camera']['default_fps'])
    return fps


def stream_camera():
    """
    Creates a socket connection to the camera address and port defined in the
    config file. Reads the data from this server and proxy's it to the client
    in chunks separated by the boundary.
    """
    conn = None
    try:
        conn = ssl.wrap_socket(socket.socket(socket.AF_INET),
                               ca_certs=config_json['camera']['cert_location'],
                               cert_reqs=ssl.CERT_REQUIRED)
        conn.connect((config_json['camera']['network_address'], config_json['camera']['port']))
        conn.send('GET /stream?fps={} HTTP/1.1\r\n'.format(str(extract_fps())) +
                  '{}: {}\r\n\r\n'.format(config_json['camera']['api_key_header_name'],
                                          config_json['camera']['api_key']))

    except Exception as e:
        print_err('Exception connecting to socket.', repr(e), e.message)
        stop_with_error('Failed to load stream.')

    try:
        buf = ''
        boundary = None
        stripped_code = False
        while True:
            buf = buf + conn.recv(READ_CHUNK_SIZE)
            if len(buf) > 0:
                if not stripped_code:
                    stripped_code, buf = strip_status_code(buf)

                if boundary is None:
                    boundary = find_boundary(buf)

                if stripped_code and boundary is not None:
                    buf = send_to_boundary(buf, boundary)
            else:
                time.sleep(NO_DATA_SLEEP_TIME)
    except Exception as e:
        print_err('Exception reading from socket.', repr(e), e.message)


def main():
    api_key = parse_api_key()
    if api_key is None:
        print_err('Accessed without an API key.')
        stop_with_error('Unauthorized', 403, 'Forbidden')

    elif config_json['api_key'] is None or len(config_json['api_key']) == 0:
        print_err('No API key defined in the config file!')
        stop_with_error('Unauthorized', 403, 'Forbidden')

    elif not config_json['api_key'] == api_key:
        print_err('Accessed with a bad API key.')
        stop_with_error('Unauthorized', 403, 'Forbidden')

    else:
        stream_camera()


with open(CONF_LOCATION, 'r') as config_file:
    config_json = json.load(config_file)
    main()
