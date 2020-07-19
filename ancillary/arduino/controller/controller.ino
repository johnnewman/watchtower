/*
  controller
  Reads the light in the room using and adjusts IR LEDs to the
  appropriate brightness. Also controls a servo to expose and hide
  the camera.
  
  Communicates serially with a microcontroller using RX_PIN and
  TX_PIN, supplying the room light value on a scale of 0-100. This
  connection can receive on/off commands to enable or disable the LEDs.
  This can also receive servo commands to move a servo to a desired
  angle.
  
  This program is designed to run on an Atmel ATtiny84 and should
  consume around 5k of program space when Link Time Optimization is
  enabled.
  
  Created June 20, 2020
  By John Newman
*/

#include <SoftwareSerial.h>
#include "TinyServo.h"

const int BAUD_RATE = 9600;
const int RX_PIN = 9;
const int TX_PIN = 10;

const int LED_PWM_PIN = 7;  // For large number of LED's, use a transistor.
const int LIGHT_SENSOR_PIN = A0;

// The analogRead light value is constrained between MAX and MIN.
const int MAX_LIGHT_THRESH = 100;
const int MIN_LIGHT_THRESH = 40;

const int SERVO_PIN = 5;
const int SERVO_MIN_PULSE_WIDTH = 500;
const int SERVO_MAX_PULSE_WIDTH = 2300;

// The valid commands received from RX_PIN.
const String IR_ON_COMMAND = "ir_on";
const String IR_OFF_COMMAND = "ir_off";
const String SERVO_ANGLE_COMMAND = "servo_angle_";
const String SUCCESS_MESSAGE = "ok";


SoftwareSerial comm(RX_PIN, TX_PIN);
TinyServo servo;

bool shouldRunIR = true;
unsigned long lastTransmission = 0;

void setup() {
  pinMode(LED_PWM_PIN, OUTPUT);
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  comm.begin(BAUD_RATE);
  servo.attach(SERVO_PIN, SERVO_MIN_PULSE_WIDTH, SERVO_MAX_PULSE_WIDTH);
  comm.println("online");
}

void loop() {
    String command = receiveCommand();
    if (command != "") {
      processServoCommand(command);
      processIRCommand(command);
    }

    if (!shouldRunIR) {
      digitalWrite(LED_PWM_PIN, LOW);
      return;
    }

    if (millis() - lastTransmission >= 500) {
      updateLED(readLight());
      lastTransmission = millis();
    }
}

/**
  Reads commands separated by newlines on RX_PIN.
  
  @return the command string or the empty string.
*/
String receiveCommand() {
  comm.listen();
  if (comm.available()) {
    return comm.readStringUntil('\n');
  }
  return "";
}

void processServoCommand(String command) {
  if (!command.startsWith(SERVO_ANGLE_COMMAND)) {
    return;
  }
  
  String angleString = command.substring(SERVO_ANGLE_COMMAND.length());
  if (angleString.length() > 0) {
    comm.println(SUCCESS_MESSAGE);
    int angle = angleString.toInt();
    servo.writeAngle(angle);
    comm.print("new angle: ");
    comm.println(angle);
  }
}

/**
 * 
 */
void processIRCommand(String command) {
  // Explicitly check for valid commands to ignore signal noise.
  if (command == IR_ON_COMMAND) {
    comm.println(SUCCESS_MESSAGE);
    shouldRunIR = true;
  } else if (command == IR_OFF_COMMAND) {
    comm.println(SUCCESS_MESSAGE);
    shouldRunIR = false;
  }
}

/**
 * Reads the analog light value on LIGHT_SENSOR_ANALOG_PIN.
 * 
 * @return The clamped/constrained light value.
 */
int readLight() {
  int light = analogRead(LIGHT_SENSOR_PIN);
  return constrain(light, MIN_LIGHT_THRESH, MAX_LIGHT_THRESH);
}

/**
  Updates the brightess of the LEDs using PWM. Also sends
  the light value from 0-100 to TX_PIN.

  @param lightValue The analog light reading from 0 to 255.
*/
void updateLED(int lightValue) {
  // Reverse it and map to 0-255 scale.
  int pwmValue = 255 - map(lightValue, MIN_LIGHT_THRESH, MAX_LIGHT_THRESH, 0, 255);
  analogWrite (LED_PWM_PIN, pwmValue);
  // Transmit light data. Avoid using floats to save memory.
  comm.print("ir: ");
  comm.println(100 - (pwmValue * 100 / 255));
}
