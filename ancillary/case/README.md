# 3D Case

The [PiSecurityCamCase.stl](./PiSecurityCamCase.stl) file is a sample case for the security system. For extra peace of mind, the camera is connected to a servo and will conceal the camera inside the case when not in use.

The case contains holes in the front that match the LED configuration of the IR panel described in the [Arduino section](../arduino). The front also contains a spot for the photoresistor and the status LED. The front panel is designed to slide down onto the two side panels, which makes servicing and installing the front hardware a little easier.

The case has a mounting cradle for a micro servo on the right side panel. The SG92R servo works great: https://www.adafruit.com/product/169. This servo rotates the top Pi Camera housing to expose the camera when the system is turned on.

The system is self-contained except for a space for the power cable. The left side panel can be removed or altered if you need access to the USB or Ethernet ports. A Raspberry Pi 3 or 4 is recommended for the on-board WiFi.

<img src="./Case_Top_Front.png" width="300" /> <img src="./Case_Bottom_Back.png" width="300" />

<img src="./Case_Exploded.png" width="500" />
