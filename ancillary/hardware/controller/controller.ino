/*
  controller
  
  Reads the analog light in the room and adjusts IR LEDs to the
  appropriate brightness. Also controls a servo to expose and hide
  the camera.
  
  Communicates serially with a microcontroller using RX_PIN and
  TX_PIN, supplying the room light value on a scale of 0-100. This
  connection can receive on/off commands to enable or disable the LEDs.
  This can also receive servo commands to move a servo to a desired
  angle.
  
  This program is designed to run on an Atmel ATtiny84 or 44 and
  should consume about 3.6KB of program space when link time optimization
  is enabled.
  
  Created by John Newman, June 20, 2020.
  MIT License.
*/

#include <SoftwareSerial.h>
#include "TinyServo.h"

const unsigned int BAUD_RATE = 19200;
const unsigned int RX_PIN = 2;
const unsigned int TX_PIN = 1;

const unsigned int LED_PWM_PIN = 7;  // For large number of LED's, use a transistor.
const unsigned int LIGHT_SENSOR_PIN = A3;

// The analogRead light value (0-255) is constrained between MIN and MAX.
const byte MIN_LIGHT_READING = 40;
const byte MAX_LIGHT_READING = 100;

const unsigned int SERVO_PIN = 5;
const unsigned int SERVO_MIN_PULSE_WIDTH = 500;
const unsigned int SERVO_MAX_PULSE_WIDTH = 2300;

// The valid commands received from RX_PIN.
const char IR_ON_COMMAND[] = "ir_on";
const char IR_OFF_COMMAND[] = "ir_off";
const char SERVO_ANGLE_COMMAND[] = "servo_angle_";

// The valid messages sent over TX_PIN.
const char SUCCESS_MESSAGE[] = "ok\n";
const char REBOOT_MESSAGE[] = "reboot\n";
const char BRIGHTNESS_PREFIX[] = "bright: ";

// Length of maximum received string. "servo_angle_1xx\n"
const byte MAX_COMMAND_LENGTH = 16;

SoftwareSerial comm(RX_PIN, TX_PIN);

TinyServo servo;

// Start in the "off" state.
bool shouldRunIR = false;

// Used to keep track of when the last transmission
// occurred. This keeps us from clogging the TX line
// while also avoiding calls to delay().
unsigned long lastTransmission = 0;


void setup() {
  pinMode(LED_PWM_PIN, OUTPUT);
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  comm.begin(BAUD_RATE);
  comm.print(REBOOT_MESSAGE);
  servo.attach(SERVO_PIN, SERVO_MIN_PULSE_WIDTH, SERVO_MAX_PULSE_WIDTH);
}

void loop() {
    char commandBuffer[MAX_COMMAND_LENGTH] = "";
    receiveCommand(commandBuffer);
    if (strlen(commandBuffer) > 0) {
      processServoCommand(commandBuffer);
      processIRCommand(commandBuffer);
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
  
  @return the command string or an empty array.
*/
void receiveCommand(char *commandBuffer) {
  comm.listen();
  if (comm.available()) {
    comm.readBytesUntil('\n', commandBuffer, MAX_COMMAND_LENGTH);
  }
}


/**
 * Parses servo commands, extracting the angle information
 * and passing that along to the TinyServo instance.
 * 
 * @param command The command string to check.
 */
void processServoCommand(const char *command) {
  if (strstr(command, SERVO_ANGLE_COMMAND) == NULL) {
    return;
  }

  const char *angleString = &command[strlen(SERVO_ANGLE_COMMAND)];
  if (strlen(angleString) > 0) {
    byte angle = atoi(angleString);
    servo.writeAngle(angle);
    sendSuccessMessage();
  }
}

/**
 * Parses infrared commands, flipping the shouldRunIR flag
 * if one is found.
 * 
 * @param command The command string to check.
 */
void processIRCommand(const char *command) {
  if (strcmp(command, IR_ON_COMMAND) == 0) {
    shouldRunIR = true;
    sendSuccessMessage();
  } else if (strcmp(command, IR_OFF_COMMAND) == 0) {
    shouldRunIR = false;
    sendSuccessMessage();
  }
}

/**
 * Reads the analog light value on LIGHT_SENSOR_ANALOG_PIN.
 * 
 * @return The clamped/constrained light value.
 */
byte readLight() {
  byte light = analogRead(LIGHT_SENSOR_PIN);
  return constrain(light, MIN_LIGHT_READING, MAX_LIGHT_READING);
}

/**
  Updates the brightess of the LEDs using PWM. Also sends
  the light value from 0-100 to TX_PIN.

  @param lightValue The analog light reading from 0 to 255.
*/
void updateLED(byte lightValue) {
  // Reverse it and map to 0-255 scale.
  byte pwmValue = map(lightValue, MIN_LIGHT_READING, MAX_LIGHT_READING, 255, 0);
  analogWrite(LED_PWM_PIN, pwmValue);
  comm.print(BRIGHTNESS_PREFIX);
  comm.print(map(pwmValue, 0, 255, 100, 0));
  comm.print('\n');
}

/**
 * Used anytime a success message is transmitted.
 */
void sendSuccessMessage() {
  comm.print(SUCCESS_MESSAGE);
}
