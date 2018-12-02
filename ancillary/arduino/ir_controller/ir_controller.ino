/*
  ir_controller
  Reads the light in the room using LIGHT_SENSOR_ANALOG_PIN and
  adjusts IR LEDs to the appropriate brightness using LED_PWM_PIN.

  Communicates serially with a microcontroller with RX_PIN and
  TX_PIN, supplying the room light value on a scale of 0-100. This
  can receive on/off commands to enable or disable the LEDs.

  This logic is designed for an Adafruit Trinket. If you use a 5
  volt Arduino to communicate with a Raspberry Pi, use a voltage
  reducer on the outgoing serial connection/TX_PIN.

  Created November 17, 2018
  By John Newman
*/

#include <SoftwareSerial.h>

const int BAUD_RATE = 9600;
const int RX_PIN = 1;
const int TX_PIN = 2;

const int LED_PWM_PIN = 0;  // For large number of LED's, use a transistor.
const int LIGHT_SENSOR_IN_PIN = 4;
const int LIGHT_SENSOR_ANALOG_PIN = 2;  // On the Trinket, Digital 4 is mapped to Analog 2.
const int TIMEOUT = 1000/4;  // 4 loops per second.

// The light value from analogRead will be clamped between MAX and MIN.
const int MAX_LIGHT_THRESH = 100;
const int MIN_LIGHT_THRESH = 40;

// The valid commands received from RX_PIN.
const String ON_COMMAND = "on";
const String OFF_COMMAND =  "off";


SoftwareSerial Comm(RX_PIN, TX_PIN);
bool shouldRun = false;

void setup() {
  pinMode(RX_PIN, INPUT);
  pinMode(TX_PIN, OUTPUT);
  pinMode(LED_PWM_PIN, OUTPUT);
  pinMode(LIGHT_SENSOR_IN_PIN, INPUT);
  Comm.begin(BAUD_RATE);
}


void loop() {
    String command = receiveCommand();
    if (command != "") {
      // Explicitly check for both commands to ignore signal noise.
      if (command == ON_COMMAND) {
        shouldRun = true;
      } else if (command == OFF_COMMAND) {
        shouldRun = false;
      }
    }

    if (!shouldRun) {
      digitalWrite(LED_PWM_PIN, LOW);
      delay(TIMEOUT);
      return;
    }

    // In running state.
    
    updateLED(readLight());
    delay(TIMEOUT);
}

/**
  Reads commands separated by newlines on RX_PIN.
  
  @return the command string or the empty string.
*/
String receiveCommand() {
  Comm.listen();
  if (Comm.available()) {
    return Comm.readStringUntil('\n');
  }
  return "";
}

/**
  Reads the analog light value on LIGHT_SENSOR_ANALOG_PIN.

  @return The clamped/constrained light value.
*/
int readLight() {
  int light = analogRead(LIGHT_SENSOR_ANALOG_PIN);
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
  Comm.println(100 - (pwmValue * 100 / 255));
}

