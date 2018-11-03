#!/usr/bin/python

import json
import os
import re
import socket
import ssl
import sys
import time


READ_CHUNK_SIZE = 4096
NO_DATA_SLEEP_TIME = 0.1
CONF_LOCATION = '/etc/piseccam/proxy_config.json'


def return_error(error_string):
    print 'Content-Type: application/json\r\n\r\n'
    print json.dumps(dict(success=False,
                          message=error_string))
    sys.exit()


def parse_api_key():
    for header_name, header_value in os.environ.iteritems():
        if header_name == config_json['api_token_header_key']:
            return header_value
    return None


def strip_status_code(buf):
    status_code_str = 'HTTP/1.1 200 OK\r\n'
    if buf.startswith(status_code_str):
        return True, buf[len(status_code_str):]
    return False, buf


def find_boundary(buf):
    result = re.search('Content-Type.*boundary=(?P<boundary>\w+)\r\n', buf)
    if result:
        return result.group('boundary')
    return None


def send_to_boundary(buf, boundary):
    boundary = '--' + boundary + '\r\n'
    index = buf.find(boundary, min(len(boundary), len(buf)))
    if index > -1:
        print(buf[:index])
        sys.stdout.flush()
        return buf[index:]
    return buf


def stream_camera():
    conn = ssl.wrap_socket(socket.socket(socket.AF_INET),
                           ca_certs=config_json['cert_location'],
                           cert_reqs=ssl.CERT_REQUIRED)
    conn.connect((config_json['camera_address'], config_json['port']))
    conn.send('GET /stream')

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


def main():
    api_key = parse_api_key()
    if api_key is None:
        return_error('Unauthorized')

    if config_json['api_token'] == api_key:
        stream_camera()
    else:
        return_error('Unauthorized')


with open(CONF_LOCATION, 'r') as config_file:
    config_json = json.load(config_file)
    main()
