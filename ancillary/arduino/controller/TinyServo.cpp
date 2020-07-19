/*
  TinyServo.cpp - Tiny library for controlling servos on
  the Atmel ATtiny24/44/84.
  Created by John Newman, June 28, 2020.
  MIT License.
*/

#include "TinyServo.h"

const int PIN_A = 6;
const int PIN_B = 5;
const int PULSE_HZ = 50;
const int TIMER_TOP = 20000;
const int MIN_PULSE_WIDTH = 1000; // 1ms
const int MAX_PULSE_WIDTH = 2500; // 2.5ms
const int SERVO_COUNT = 2;

static TinyServo *servos[SERVO_COUNT];

TinyServo::TinyServo() { }

void TinyServo::attach(int pin) {
  this->attach(pin, MIN_PULSE_WIDTH, MAX_PULSE_WIDTH);
}

void TinyServo::attach(int pin, int minPulseWidth, int maxPulseWidth) {

  int index;
  switch (pin) {
    case PIN_A:
      index = 0;
      break;
    case PIN_B:
      index = 1;
      break;
    default:
      // Unsupported pin.
      return;
  }

  if (servos[index]) {
    return;
  }
  servos[index] = this;

  /*
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
  cli(); // Disable interrupts while changing registers.
  TCCR1A = _BV(WGM11);
  TCCR1B = _BV(CS11) | _BV(WGM12) | _BV(WGM13);
  ICR1 = TIMER_TOP;
  sei(); // Reenable interrupts.
  
  _minPulseWidth = minPulseWidth;
  _maxPulseWidth = maxPulseWidth;
  _pin = pin;
  pinMode(pin, OUTPUT);
}

void TinyServo::writeAngle(int angle) {
  angle = constrain(angle, 0, 180);
  cli();
  *(_connect()) = map(angle, 0, 180, _minPulseWidth, _maxPulseWidth);
  sei();
}

int* TinyServo::_connect() {
  /*
   Bits COM1n1 COM2n1
             1     0
   Sets OC1n to low on compare match with OCR1n. Sets to high at bottom.
   n=A if pin==PIN_A, n=B if pin==PIN_B.
  */
  switch (_pin) {
    case PIN_A:
      TIMSK1 |= _BV(OCIE1A);
      TCCR1A |= _BV(COM1A1);
      return &OCR1A;
    case PIN_B:
      TIMSK1 |= _BV(OCIE1B);
      TCCR1A |= _BV(COM1B1);
      return &OCR1B;
  }
}

void TinyServo::_disconnect() {
  switch (_pin) {
    case PIN_A:
      TIMSK1 &= ~_BV(OCIE1A);
      TCCR1A &= ~_BV(COM1A1);
      break;
    case PIN_B:
      TIMSK1 &= ~_BV(OCIE1B);
      TCCR1A &= ~_BV(COM1B1);
      break;
  }
}

// Called for every pulse on the servo's control pin, which pulses
// 50 times a second. After 1 second, we disconnect the servo.
void TinyServo::interrupt() {
  _pulseCount++;
  if (_pulseCount >= PULSE_HZ) {
    cli();
    _disconnect();
    sei();
    _pulseCount = 0;
  }
}

/** Timer1 interrupt handlers **/

ISR(TIMER1_COMPA_vect)  {
  if (servos[0]) {
    servos[0]->interrupt();
  }
}

ISR(TIMER1_COMPB_vect)  {
  if (servos[1]) {
    servos[1]->interrupt();
  }
}
