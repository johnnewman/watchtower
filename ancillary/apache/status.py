#!/usr/bin/python

import cgi_common as cgic

if cgic.verify_api_key():
    cgic.controller.status()
