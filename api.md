# Watchtower HTTP API

### GET `/status` 

Returns the current monitoring status of Watchtower.

#### 200 Response JSON:
```JSON
{
    "monitoring": true
}
```

### GET `/start`

Starts monitoring the camera feed for motion. If the optional microcontroller is used, it will be signaled to move its servo to the on position and start monitoring the room brightness to control infrared lighting.

The response will match the format of the `/status` response.

#### 200 Response JSON:
```JSON
{
    "monitoring": true
}
```

### GET `/stop`

Stops monitoring the camera feed for motion. If the optional microcontroller is used, it will be signaled to move its servo to the off position and stop monitoring the room brightness to control infrared lighting. The infrared lighting will be turned off.

The `/stop` endpoint is the exact opposite of `/start`.

#### 200 Response JSON:
```JSON
{
    "monitoring": false
}
```

### GET `/config`

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

### POST `/config`

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

### GET `/record`

Triggers a recording event. The event will be padded both before and after the trigger event by the value defined in `MOTION_RECORDING_PADDING` in `watchtower_config.json`. An example of this file is located in [watchtower_config_example.json](watchtower/config/watchtower_config_example.json).

The response will be a 204 No Content.

### GET `/stream`

Starts an MJPEG stream that will send JPEG frames as a multipart response. This will continue to stream until the connection is closed.

The response will be a 200. Each part will have a Content-Type of `image/jpeg` and the raw JPEG data will be delineated by a `-- FRAME` boundary string.
