/*
  TinyServo.h - Tiny library for controlling servos on
  the Atmel ATtiny24/44/84.
  Created by John Newman, June 28, 2020.
  MIT License.
*/

#ifndef TinyServo_h
#define TinyServo_h

#include "Arduino.h"

class TinyServo {
  public:
    TinyServo();

    // Sets up the pin for output and initializes the timer.
    void attach(int pin);

    // Sets up the pin for output and initializes the timer.
    void attach(int pin, int minPulseWidth, int maxPulseWidth);

    // Moves the servo to the specified angle from 0 to 180.
    void writeAngle(int angle);

    void interrupt();
    
  private:
    int _pin;
    int _minPulseWidth;
    int _maxPulseWidth;
    int _pulseCount;

    // Disconnects the servo's pin from the timer and disables
    // interrupts for the servo's timer register.
    void _disconnect();

    // Connects the servo's pin to the timer running in PWM mode.
    // This also enables interrupts for every pulse.
    int* _connect();
};

#endif
