# 3D Case

The cases for watchtower are contained here, in their versioned folders.

### All versions:

- For extra peace of mind, the camera is connected to a servo which will conceal the camera inside the case when not in use.
- The case contains holes in the front that match the LED configuration of the IR panel described in the [microcontroller section](../arduino). 
- The front also has a spot for the photoresistor and the status LED to be mounted.
- A mounting cradle for a micro servo is located on the right side panel. The SG92R servo is what I use: https://www.adafruit.com/product/169. This servo rotates the top Pi Camera housing to expose the camera when the system is turned on.
- The system is self-contained except for a space for the power cable. A Raspberry Pi 3 or 4 is recommended for the on-board WiFi.

### Version 2:

- 33% smaller than version 1.
- Uses M2x5 and M2x6 screws to stay sealed.
- Comes with mounts on the left side panel for a 30x30mm fan to cool the hardware.
- Has a tighter seal around the camera's case.
- The servo's mouting gear attaches directly to the camera's case instead of needing to use a plastic arm that comes with the servo.
- There is a cradle underneath the camera that v1 does not have. This keeps the internals from being damaged if pressure is applied to the top of the case or if the servo is commanded to rotate beyond its closing angle.

### Version 1:

This is an obsolete design that's much larger with sharper corners. It doesn't have any protection for the camera if pressure happens to be applied to the top of the case. This can cause the camera to rotate into the case or possibly break from the servo.

<img src="./v1/Case_Top_Front.png" width="300" /> <img src="./v1/Case_Bottom_Back.png" width="300" />

<img src="./v1/Case_Exploded.png" width="500" />
