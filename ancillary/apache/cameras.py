#!/usr/bin/python

import cgi_common as cgic

"""
Sends a JSON dictionary containing every camera name. Useful for knowing the
camera count and for accessing mjpeg_proxy.py.
"""

if cgic.verify_api_key():
    cgic.send_response({'cameras': cgic.controller.cameras.keys()})
