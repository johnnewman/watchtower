/*
  TinyServo.cpp - Tiny library for controlling servos on
  the Atmel ATtiny24/44/84.
  Created by John Newman, June 28, 2020.
  MIT License.
*/

#include "TinyServo.h"

const int PIN_A = 6;
const int PIN_B = 5;
const int TIMER_TOP = 20000;
const int MIN_PULSE_WIDTH = 1000; // 1ms
const int MAX_PULSE_WIDTH = 2500; // 2.5ms

TinyServo::TinyServo() { }

void TinyServo::attach(int pin) {
  this->attach(pin, MIN_PULSE_WIDTH, MAX_PULSE_WIDTH);
}

void TinyServo::attach(int pin, int minPulseWidth, int maxPulseWidth) {
  /*
   Bits COM1n1 COM2n1
             1     0
     Sets OC1n to low on compare match with OCR1n. Sets to high at bottom.
     n=A if pin==PIN_A, n=B if pin==PIN_B.
     
   Bits WGM10 WGM11 WGM12 WGM13
            0     1     1     1
     Uses fast PWM with TOP value set to value of register ICR1         
   
   Bits CS10 CS11 CS12
           0    1    0
     Sets prescaler to 8.
   
   
   PWM frequency = Timer clock / prescaler / TOP value
   PWM Freq = 8 MHz / 8 / 20000
            = 50 Hz
  */
  
  switch (pin) {
    case PIN_A:
      pinMode(pin, OUTPUT);
      TCCR1A = _BV(TCCR1A) | _BV(COM1A1) | _BV(WGM11);
      _compareRegister = &OCR1A;
      break;
      
    case PIN_B:
      pinMode(pin, OUTPUT);
      TCCR1A = _BV(TCCR1A) | _BV(COM1B1) | _BV(WGM11);
      _compareRegister = &OCR1B;
      break;
      
    default:
      // Unsupported pin.
      return;
  }
  TCCR1B =  _BV(CS11) | _BV(WGM12) | _BV(WGM13);
  ICR1 = TIMER_TOP;
  _minPulseWidth = minPulseWidth;
  _maxPulseWidth = maxPulseWidth;
 }

void TinyServo::writeAngle(int angle) {
  angle = constrain(angle, 0, 180);
  *_compareRegister = map(angle, 0, 180, _minPulseWidth, _maxPulseWidth);
}
