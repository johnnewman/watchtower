import json
import requests
import cgi_common

TIMEOUT = 5


class CameraController(object):
    """
    Class that houses camera config data that the CGI scripts can use for
    convenience.

    TODO: Handle multiple cameras. Search each cameras responses for errors.
    """

    def __init__(self, config_location):
        super(CameraController, self).__init__()
        with open(config_location, 'r') as config_file:
            config_json = json.load(config_file)
            self.camera = Camera(config_json['camera'])

    def stop(self):
        self.camera.stop()

    def start(self):
        self.camera.start()

    def status(self):
        self.camera.status()


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

    def stop(self):
        self.__send_get_to_endpoint('stop')

    def start(self):
        self.__send_get_to_endpoint('start')

    def status(self):
        self.__send_get_to_endpoint('status')

    def __send_get_to_endpoint(self, endpoint):
        """
        Will perform an HTTP GET request to the ``endpoint``. Response JSON
        is sent to stdout. Any error will be caught and a generic error sent to
        stderr.

        :param endpoint: The endpoint to access using a GET request.
        """
        url = 'https://{}:{}/{}'.format(self.network_address, self.port, endpoint)
        headers = {self.api_key_header_name: self.api_key}
        try:
            response = requests.get(url=url, verify=self.cert_location, headers=headers, timeout=TIMEOUT)
            if response.status_code == 200:
                try:
                    cgi_common.send_response(json_dict=response.json())
                except ValueError:
                    self.send_error_response()
            else:
                self.send_error_response()
        except requests.exceptions.ConnectionError:
            self.send_error_response()
        except requests.exceptions.ReadTimeout:
            self.send_error_response()

    @staticmethod
    def send_error_response():
        cgi_common.send_error_message('Error reading response from camera.',
                                      503,
                                      'Service Unavailable')
