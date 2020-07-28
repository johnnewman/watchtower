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

    /**
     * Sets up the pin for output and initializes the timer.
     */
    void attach(byte pin);

    /**
     * Sets up the pin for output and initializes the timer. The pulse
     * widths are in microseconds, so a 2.5 millisecond pulse width
     * should be specified as 2500.
     */
    void attach(byte pin, unsigned int minPulseWidth, unsigned int maxPulseWidth);

    /**
     * Moves the servo to the specified angle from 0 to 180.
     */
    void writeAngle(byte angle);

    /**
     * Called for every pulse on the servo's control pin, which pulses
     * 50 times a second. After 1 second, we disconnect the servo.
     */
    void interrupt();
    
  private:
  
    byte _pin;
    
    unsigned int _minPulseWidth;
    
    unsigned int _maxPulseWidth;
    
    byte _pulseCount;
    
    /**
     * Disconnects the servo's pin from the timer and disables
     * interrupts for the servo's timer register.
     */
    void _disconnect();

    /**
     * Connects the servo's pin to the timer running in PWM mode.
     * This also enables interrupts for every pulse. Returns a
     * pointer to the OCR1x register.
     */
    volatile unsigned int* _connect();
};

#endif
