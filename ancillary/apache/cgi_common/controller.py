import json
import requests
import cgi_common
from threading import Thread, Lock

TIMEOUT = 5
SUPPORTED_ENDPOINTS = ['start', 'stop', 'status']


class CameraController(object):
    """
    Class that houses camera config data that the CGI scripts can use for
    convenience. This supports multiple cameras.
    """

    def __init__(self, config_location):
        super(CameraController, self).__init__()
        with open(config_location, 'r') as config_file:
            config_json = json.load(config_file)
            self.cameras = {}
            for cam_name in config_json['cameras']:
                self.cameras[cam_name] = Camera(config_json['cameras'][cam_name])

    def stop(self):
        self.__handle_bulk_requests('stop')

    def start(self):
        self.__handle_bulk_requests('start')

    def status(self):
        self.__handle_bulk_requests('status')

    def __handle_bulk_requests(self, endpoint):
        """
        Iterates through every camera and hits the supplied endpoint. Once
        every request is finished, the combined response is sent to std out.
        :param endpoint: The endpoint to access using a GET request.
        """
        lock = Lock()
        responses = {}
        for cam_name in self.cameras:
            def thread_callback(name, data):
                cgi_common.err('Received callback from %s' % cam_name)
                lock.acquire()
                responses[name] = data
                lock.release()
                if len(responses) == len(self.cameras):
                    cgi_common.send_response(responses)
            camera = self.cameras[cam_name]
            thread = camera.request_thread(endpoint)
            thread.set_callback(thread_callback)
            thread.camera_name = cam_name
            thread.start()


class Camera(object):
    """
    Class that houses the config data for accessing one camera over the HTTP.
    """

    def __init__(self, cam_json):
        super(Camera, self).__init__()
        self.api_key = cam_json['api_key']
        self.api_key_header_name = cam_json['api_key_header_name']
        self.network_address = cam_json['network_address']
        self.port = cam_json['port']
        self.cert_location = cam_json['cert_location']
        self.default_mjpeg_fps = cam_json['default_fps']

    def request_thread(self, endpoint):
        """
        Will create a ``CameraRequest`` instance using the provided endpoint.
        Only works for supported endpoints. Returns this thread for further
        configuration.

        :param endpoint: The endpoint to access using a GET request.
        """
        if endpoint not in SUPPORTED_ENDPOINTS:
            return None

        url = 'https://{}:{}/{}'.format(self.network_address, self.port, endpoint)
        headers = {self.api_key_header_name: self.api_key}
        return CameraRequest(url=url, headers=headers, cert_location=self.cert_location)


class CameraRequest(Thread):
    """
    Threaded class for performing a GET request on a camera endpoint. Data is
    sent to a callback as a dictionary.
    """

    def __init__(self, url, headers, cert_location):
        super(CameraRequest, self).__init__()
        self.__url = url
        self.__headers = headers
        self.__cert_location = cert_location
        self.__callback = None
        self.__camera_name = None

    @property
    def camera_name(self):
        return self.__camera_name

    @camera_name.setter
    def camera_name(self, value):
        self.__camera_name = value

    def set_callback(self, value):
        self.__callback = value

    def run(self):
        try:
            response = requests.get(url=self.__url,
                                    verify=self.__cert_location,
                                    headers=self.__headers,
                                    timeout=TIMEOUT)
            if response.status_code == 200:
                try:
                    self.__hit_callback_with_dict(response.json())
                except ValueError:
                    self.__hit_callback_with_error('Error parsing response.')
            else:
                self.__hit_callback_with_error('Received bad status code.')
        except requests.exceptions.ConnectionError:
            self.__hit_callback_with_error('Connection error.')
        except requests.exceptions.ReadTimeout:
            self.__hit_callback_with_error('Timeout error.')
        except Exception:
            self.__hit_callback_with_error('Unhandled exception.')

    def __hit_callback_with_dict(self, dictionary):
        self.__callback(self.camera_name, dictionary)

    def __hit_callback_with_error(self, error_string):
        self.__callback(self.camera_name, cgi_common.create_error_dict(error_string))
