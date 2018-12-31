# Protoboard schematic

This uses two Adafruit boards:
- Perma-Proto HAT
   - https://www.adafruit.com/product/2310
   - ![Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/Adafruit%20Perma-Proto%20HAT.fzpz)
- PermaProto Quarter-sized breadboard
   - https://www.adafruit.com/product/1608
   - ![Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/PermaprotoQuarterBoard.fzpz)

A status LED is included to ensure that the user knows the infrared lights are turned on. Infrared radiation is something to definitely avoid hitting your eyes!  This status light can be used as a baseline safety check to ensure the lights are indeed on or off. It is connected to the same PWM line as the IR LEDs, so its brightness will update with the front IR panel.

![Schematic](ArduinoHat_bb.png)
