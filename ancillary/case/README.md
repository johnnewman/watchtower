# System case

The cases for Watchtower are housed within their versioned folders here. You can check out the full model of v2 [here](./v2/parts/v2_all_parts.stl).

### All versions:

For extra peace of mind, the camera is connected to a servo which will conceal the camera inside the case when not in use. The case contains holes in the front that match the LED configuration of the IR panel described in the [hardware section](../hardware), along with ports for a photoresistor and status LED.

A mounting cradle for the micro servo is located on the right side panel. The SG92R servo is what I use: https://www.adafruit.com/product/169. The servo will rotate the camera housing to expose the camera when the system is turned on.

The system is self-contained except for a space for the power cable. A Raspberry Pi 3 or 4 is necessary for the on-board WiFi.

### Version 2:

- 32% smaller than version 1.
- Uses M2x5 and M2x6 screws to tightly seal all of its panels.
- Comes with mounts on the left side panel for a 30x30mm fan to cool the system.
- The top panel has a closer seal around the camera's case.
- The servo's mouting gear attaches directly to the camera's case instead of needing to use a plastic arm that comes with the servo.
- There is a cradle underneath the camera that v1 does not have. This keeps the camera mount from being damaged if pressure is applied to the top of the case or if the servo is rotated beyond its closed angle.

<img src="./v2/v2_top_front.png" width="250" /> <img src="./v2/v2_bottom_back.png" width="250" />
<img src="./v2/v2_exploded.png" width="300" />

### Version 1:

This is an obsolete design that's much larger. It doesn't have any protection for the camera if pressure happens to be applied to the top of the case. This can cause the camera to rotate into the case or possibly break from the servo.

<img src="./v1/v1_top_front.png" width="250" /> <img src="./v1/v1_bottom_back.png" width="250" />
<img src="./v1/v1_exploded.png" width="300" />
