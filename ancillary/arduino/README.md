# Protoboard schematic

This uses two Adafruit prototyping boards and one microcontroller:
- Perma-Proto HAT
   - https://www.adafruit.com/product/2310
   - [Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/Adafruit%20Perma-Proto%20HAT.fzpz)
- PermaProto Quarter-sized breadboard
   - https://www.adafruit.com/product/1608
   - [Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/PermaprotoQuarterBoard.fzpz)
- Trinket 5V
   - https://www.adafruit.com/product/1501
   - [Fritzing file](https://github.com/adafruit/Fritzing-Library/blob/master/parts/Adafruit%20Trinket%205V.fzpz)


The Perma-Proto HAT sits on top of the Raspberry Pi and contains ports to run the servo, front IR panel, status LED, and photoresistor. This setup will all fit inside the [case included with the project](../case).

A status LED is included to help the user know that the infrared lights are turned off. It is connected to the same PWM line as the IR LEDs, so its brightness will update with the front IR panel.

**If you use a 5 volt Arduino to communicate with a Raspberry Pi, use a voltage reducer on the outgoing serial connection/TX_PIN (included in diagram).** The Raspberry Pi should only communicate over 3.3 volt connections.

![Schematic](ArduinoHat_bb.png)
