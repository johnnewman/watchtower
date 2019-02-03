# Protoboard schematic

This uses two Adafruit prototyping boards and one microcontroller:
- Perma-Proto HAT
   - https://www.adafruit.com/product/2310
   - ![Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/Adafruit%20Perma-Proto%20HAT.fzpz)
- PermaProto Quarter-sized breadboard
   - https://www.adafruit.com/product/1608
   - ![Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/PermaprotoQuarterBoard.fzpz)
- Trinket 5V
   - https://www.adafruit.com/product/1501
   - ![Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/Adafruit%20Trinket%205V.fzpz)


The Perma-Proto HAT sits on top of the Raspberry Pi and contains ports to run the servo, front IR panel, status LED, and photoresistor. This setup will all fit inside the ![case included with the project](../case).

A status LED is included to ensure that the user knows the infrared lights are turned on. Infrared radiation is something to avoid hitting your eyes! This status light can be used to ensure the lights are indeed on or off. It is connected to the same PWM line as the IR LEDs, so its brightness will update with the front IR panel.

![Schematic](ArduinoHat_bb.png)
