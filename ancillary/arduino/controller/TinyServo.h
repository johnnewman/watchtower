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
    void writeAngle(int angle);
  private:
    int *_compareRegister;
    int *_minPulseWidth;
    int *_maxPulseWidth;
};

#endif
