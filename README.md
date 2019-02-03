# Pi Security Camera

### Overview

This is a Raspberry Pi program that will detect motion on a Pi camera's feed and save the h264 video to disk and Dropbox.  The entry point of the program is [pi_sec_cam.py](pi_sec_cam.py). 

This project is designed for the NoIR camera and contains an Arduino program that it can communicate with to read analog room brightness and control infrared LEDs for night vision.

A 3D model of a case for the system is located in ![ancillary/case/](ancillary/case/). This houses the Raspberry Pi, camera, Arduino, servo, array of IR LEDs, photoresistor, and a status LED. Along with the case, a Fritzing prototype of the system is included in ![ancillary/arduino/](ancillary/arduino).

<img src="ancillary/case/Case_XRay.png" width="300" />

This project hosts a simple web server to interface with the camera and stream an MJPEG feed. It contains Apache CGI scripts to create a single endpoint that can proxy with multiple Pi Security Camera instances.

By default, motion events are stored to disk in the format: `cam_name/%Y-%m-%d/%H.%M.%S/video.h264`

The rest of this readme breaks down each component and describes its corresponding configuration located in [config/camera_config.json](config/camera_config.json).
 1. [Motion Detection](#1-motion-detection)
 2. [Dropbox File Upload](#2-dropbox-file-upload)
 3. [Arduino/Infrared](#3-arduinoinfrared)
 4. [Local Server](#4-local-server)
 5. [Apache Proxy](#5-apache-proxy)
 6. [Servos](#6-servos)
 
<hr />

### 1. Motion Detection

Motion is detected using background subtraction in [motion/motion_detector.py](motion/motion_detector.py). The implementation is based heavily on this article: https://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/. A blurred grayscale image of the current camera frame is generated and subtracted from a static image of the scene. If a large enough area (`min_trigger_area`) of pixels are over the delta threshold (`min_pixel_delta_trigger`), they trigger a motion event and the area is outlined in the image. This image will be saved along with the video.

#### Config

In the `motion` object of `config/camera_config.json`:
- `max_event_time` is the maximum number of seconds for a single recording before a new base frame is selected. This is a failsafe to avoid infinitely recording in the event that the scene is permanently altered.
- `min_trigger_area` the minimum percentage (represented as a float between 0 and 1) of the image that must be detected as motion before a motion event is triggered.
- `min_pixel_delta_trigger` the minimum delta value between the base frame and current frame that marks the pixel as a motion area. This is on a scale of 0-255.
- `rec_sec_after` the number of seconds to record after motion stops.
- `rec_sec_before` the number of seconds before the motion event that should be included in the recording.

### 2. Dropbox File Upload

Video files are sent to Dropbox in small chunks as soon as motion is detected. Splitting the recording into small files keeps network failures from adversely affecting the overall quantity of saved footage.

Because the bytes of the h264 stream are broken into files, the files are not cleanly separated by header frames. For smooth playback, the data will need to be concatenated into a single file. To help with this, a bash script located at [ancillary/mp4_wrapper.sh](ancillary/mp4_wrapper.sh) will combine the videos for each motion event into one file and will convert the h264 format into mp4 using [MP4Box](https://gpac.wp.imt.fr/mp4box/). 

#### Config

In the `dropbox` object:
- `file_chunk_megs` determines the maximum file size in megabytes that will be uploaded to Dropbox. Files are saved in series using the name `video#.h264` like `video0.h264`, `video1.h264`, etc..
- `token` is the Dropbox API token for your account. If `null` is supplied, Dropbox will not be used.

### 3. Arduino/Infrared

The project can be optionally configured to work with a micro controller to turn on/off infrared lighting for night vision. A schematic for the Arduino and IR LED circuit ![is included](/ancillary/arduino).

An Arduino program located in [ancillary/arduino/ir_controller/ir_controller.ino](ancillary/arduino/ir_controller/ir_controller.ino) is configured to communicate serially with the PySecCam program. It's small enough to fit on an Adafruit Trinket/Atmel Attiny85, which is what the circuit diagram uses.  The Arduino reads the analog room brightness and uses PWM to change the LED brightness.

The serial connection is operated by [remote/ir_serial.py](remote/ir_serial.py). This module is also configured to read the room brightness value from the serial connection, which will be displayed in the camera feed's annotation area.

#### Config

In the `infrared_controller` object:
- `enabled` will determine if infrared is used. If `false`, the `ir_serial` module will be avoided.
- `baudrate` is the baudrate of the serial connection.
- `on_command` is the string written over the serial connection that turns on the room brightness sensing and IR controls.
- `off_command` string that turns off the room brightness sensing and IR controls.
- `serial_port` is the location of the serial connection, like `"/dev/serial0"` on Raspbian.
- `serial_timeout` is the time in seconds to wait for serial transmission timeouts.
- `updates_per_sec` the number serial loops per second. Each loop writes any pending commands and reads the room brightness. 

### 4. Local Server

The program contains a basic HTTP web server implementation at [remote/command_server.py](remote/command_server.py).  This can receive start and stop commands, send the camera status, and also stream the feed using the MJPEG protocol.  The server is configured to use SSL and perform client validation using a secret HTTP header field.  _The web server is not intended to face the internet._

#### API

- `/status` will send back `{"running":true/false}`. 
- `/start` will start monitoring and return the same payload as `/status`.
- `/stop` will stop monitoring and return the same payload as `/status`.
- `/stream` will start an MJPEG stream. `fps` is an optional float parameter that specifies how many JPEGs per second to stream.

#### Config

In the `server` object:
- `enabled` determines if the server will be used.
- `api_key` is the secret value in the HTTP header that is allowed to access the API. Values that do not match this string will result in an API error.
- `api_key_header_name` is the name of the HTTP header that contains the `api_key`.
- `certfile_path` the path of the certfile for SSL.
- `keyfile_path` the path of the keyfile for SSL.
- `mjpeg_framerate_cap` the maximum number of JPEGs per second that the `/stream` endpoint will allow. This is useful to avoid consuming bandwidth. 
- `server_port` the port that the server uses for connections.

### 5. Apache Proxy

This project comes with server-side Python CGI scripts that work on Apache 2, located in [ancillary/apache/](ancillary/apache). These scripts proxy commands to a series of PySecCam instances that rest behind your firewall. Each python file in that directory corresponds to an endpoint.

The `cgi_common` package located in ![ancillary/apache/cgi_common/](ancillary/apache/cgi_common) contains convenience modules and functions that are shared throughout the endpoints. This includes functionality to send JSON back to the client, log errors, verify API keys, hit endpoints on each camera, and coalesce the camera responses into one JSON response for the client.

#### Config

Configuration for the Apache proxy is located in [ancillary/apache/config/proxy_config.json](ancillary/apache/config/proxy_config.json). By default, this file should be located on the web server in `/etc/piseccam/proxy_config.json`. This path can be configured in [cgi_common/__init__.py](/ancillary/apache/cgi_common/__init__.py).

The keys are as follows:
- `api_key` the API key that will allow access to the proxy endpoints. Values that do not match this string will result in an API error.
- `api_key_header_name` is the name of the HTTP header that contains the `api_key`.
- `cameras` an object containing a series of key/value pairs where each key is a camera name. Many of these fields will match the `server` object of the [Local Server](#4-local-server) section above. Each `camera` value contains:
   - `api_key_header_name` the name used for the HTTP header containing the key. This corresponds to `api_key_header_name` of the camera's `server` config object.
   - `api_key` is the secret value in the HTTP header that is allowed to access the camera API. This corresponds to `api_key` of the camera's `server` config object.
   - `port` the port to connect to the camera's server. This corresponds to `server_port` of the camera's `server` config object.
   - `cert_location` is the location of the certfile for accessing the camera's server. This is the same file that `certfile_path` points to in the camera's `server` config object.
   - `default_fps` is the FPS to use if none is supplied, when hitting the `/stream` endpoint on the camera.

 ### 6. Servos
 
 In the event that the camera should rotate or be covered when not in use, any number of servos can be controlled with this program. This makes use of [PiServoServer](https://github.com/johnnewman/PiServoServer) to command each servo connected to the Pi.  
 
 #### Config
 
 In the `servos` array, each object represents one physical servo and contains:
 - `board_pin` the board numbering pin of the servo
 - `angle_off` the angle (from 0-180) of the servo for the off state
 - `angle_on` the angle (from 0-180) of the servo for the on state 
