# Watchtower HTTP API

### GET `/api/status` 

Returns the current monitoring status of Watchtower.

#### 200 Response JSON:
```JSON
{
    "monitoring": true
}
```

### GET `/api/start`

Starts monitoring the camera feed for motion. If the optional microcontroller is used, it will be signaled to move its servo to the on position and start monitoring the room brightness to control infrared lighting.

The response will match the format of the `/status` response.

#### 200 Response JSON:
```JSON
{
    "monitoring": true
}
```

### GET `/api/stop`

Stops monitoring the camera feed for motion. If the optional microcontroller is used, it will be signaled to move its servo to the off position and stop monitoring the room brightness to control infrared lighting. The infrared lighting will be turned off.

The `/stop` endpoint is the exact opposite of `/start`.

#### 200 Response JSON:
```JSON
{
    "monitoring": false
}
```

### GET `/api/config`

Returns the Pi camera's current image configuration. Without having made any configuration changes, this will return default values for [PiCamera](https://picamera.readthedocs.io/en/release-1.13/api_camera.html). Otherwise, these values will match the custom configuraiton preferences saved to `camera_config.json`, which are loaded and applied when Watchtower boots. This file is created and maintained automatically by Watchtower.

#### 200 Response JSON:

```JSON
{
    "awb_mode": "auto",
    "brightness": 50,
    "contrast": 0,
    "exposure_compensation": 0,
    "exposure_mode": "auto",
    "image_effect": "none",
    "iso": 0,
    "meter_mode": "average",
    "rotation": 0,
    "saturation": 0,
    "sharpness": 0,
    "video_denoise": true
}
```

### POST `/api/config`

Sets the Pi camera's image configuration settings. Any number of these fields can be sent in the POST, no need to send all of them. When changed, the new configuration will be saved to `camera_config.json` located in the Flask instance folder. Any changes will go into effect immediately, even while recording or streaming is taking place. The next time the system reboots, the updated `camera_config.json` file will be used, so these values don't need to be repeatedly reset.

#### Request JSON:

```JSON
{
    "awb_mode": "shade",
    "brightness":55,
    "exposure_mode": "night"
}
```

#### 200 Response JSON:

```JSON
{
    "awb_mode": "shade",
    "brightness": 55,
    "contrast": 0,
    "exposure_compensation": 0,
    "exposure_mode": "night",
    "image_effect": "none",
    "iso": 0,
    "meter_mode": "average",
    "rotation": 0,
    "saturation": 0,
    "sharpness": 0,
    "video_denoise": true
}
```

### GET `/api/record`

Triggers a recording event. The event will be padded both before and after the trigger event by the value defined in `MOTION_RECORDING_PADDING` in `watchtower_config.json`. An example of this file is located in [watchtower_config_example.json](watchtower/config/watchtower_config_example.json).

The response will be a 204 No Content.

### GET `/api/recordings`

Returns a listing of all recordings that Watchtower has saved to disk. Each `day` string will match the `DIR_DAY_FORMAT` in the watchtower_config.json file. Each time string in the day's `times` array will match the `DIR_TIME_FORMAT`.

200 Response JSON:
```JSON
[

    {
        "day": "2020-09-07",
        "times": [
            "12.25.43",
            "12.13.12"
        ]
    },
    {
        "day": "2020-09-06",
        "times": [
            "18.21.52",
            "14.28.26",
            "13.39.21",
            "13.02.22",
            "10.51.26",
            "10.21.05"
        ]
    }
]
```

### GET `/api/recordings/:day`

Returns a listing of all recordings for the specified day. The `day` path element must match the `DIR_DAY_FORMAT` in the watchtower_config.json file.

200 Response JSON:
```JSON
[
    "18.21.52",
    "14.28.26",
    "13.39.21",
    "13.02.22",
    "10.51.26",
    "10.21.05"
]
```

### DELETE `/api/recordings/:day`
### DELETE `/api/recordings/:day/:time`

If just a `day` is supplied, this will delete all of the recordings for the specified day. If both a `day` and `time` are supplied, this will delete only a single recording matching the day and time.

When successful, the response will be a 204 No Content.

### GET `/api/recordings/:day/:time/trigger`

Returns the jpeg image capturing the motion event that triggered the recording for the specified day and time.

The response will be a 200 containing the jpeg file data.

### GET `/api/recordings/:day/:time/recording`

Returns the h264 video file containing the entire recording that occurred at the specified day and time.

The response will be a 200 containing the h264 file data.

### GET `/stream`

_This one is treated as part of the web app, but listing it here for completeness._

Starts an MJPEG stream that will send JPEG frames as a multipart response. This will continue to stream until the connection is closed. An optional `encoding` URL parameter can be supplied with a value of `base64`, which will base64 encode each response's jpeg data.

The response will be a 200. Each part will have a Content-Type of `image/jpeg` and the raw JPEG data will be delineated by a `-- FRAME` boundary string.
