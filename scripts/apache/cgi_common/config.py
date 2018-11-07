import json


class CGIConfig(object):
    def __init__(self, config_location):
        super(CGIConfig, self).__init__()
        with open(config_location, 'r') as config_file:
            config_json = json.load(config_file)
            self.api_key = config_json['api_key']
            self.api_key_header_name = config_json['api_key_header_name']
