# 3D Case

The ![PiSecurityCamCase.stl](./PiSecurityCamCase.stl) file is a case for the security system. The case is designed to conceal the camera when it is not in use. If the system is compromised by an attacker, viewing the stream will only reveal the inside of the case unless the servo is rotated to expose the camera. This analog component of the camera moving provides extra peace of mind.

The case contains holes in the front that match the LED configuration of the IR panel described in the ![Arduino section](../arduino). The front also contains a spot for the photoresistor and the status LED. The front panel is designed to slide down onto the two side panels, which makes servicing and installing the front hardware a little easier.

The case has a mounting cradle for a micro servo on the right side panel. The SG92R servo works well: https://www.adafruit.com/product/169. This servo rotates the top Pi Camera housing to expose the camera when the system is turned on.

**The system is self-contained except for a space for the micro USB power cable.** The left side panel can be removed if you need access to the USB/Ethernet ports. A Raspberry Pi 3 is recommended for its on-board wifi. The SD card is intentionally concealed, but some small adjustments can be made to include an access slot.

<img src="./Case_Top_Front.png" width="300" /> <img src="./Case_Bottom_Back.png" width="300" />

<img src="./Case_Exploded.png" width="500" />
