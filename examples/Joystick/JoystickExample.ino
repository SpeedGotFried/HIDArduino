/*
 * Arduino HID Joystick Example
 * 
 * This sketch demonstrates how to use an Arduino with ATmega32U4 
 * (like Leonardo, Micro) as a joystick HID device.
 * 
 * It uses two analog inputs for X and Y axes, and two buttons for 
 * joystick buttons.
 * 
 * Note: This requires the Joystick library by Matthew Heironimus
 * https://github.com/MHeironimus/ArduinoJoystickLibrary
 * 
 * Hardware:
 * - Potentiometer connected to A0 (X-axis)
 * - Potentiometer connected to A1 (Y-axis)
 * - Button connected to pin 2 and GND (button 1)
 * - Button connected to pin 3 and GND (button 2)
 * - Arduino with native USB support (Leonardo, Micro, etc.)
 */

#include <Joystick.h>

// Create the Joystick
Joystick_ Joystick;

// Analog pins for potentiometers
const int xAxis = A0;
const int yAxis = A1;

// Button pins
const int button1Pin = 2;
const int button2Pin = 3;

// Variables to store previous button states
int lastButton1State = 0;
int lastButton2State = 0;

void setup() {
  // Initialize Button Pins as inputs with pull-up resistors
  pinMode(button1Pin, INPUT_PULLUP);
  pinMode(button2Pin, INPUT_PULLUP);

  // Initialize Joystick Library
  Joystick.begin();
}

void loop() {
  // Read analog values for X and Y axes
  int xValue = analogRead(xAxis);
  int yValue = analogRead(yAxis);
  
  // Map analog readings (0-1023) to joystick range (-127 to 127)
  int xMapped = map(xValue, 0, 1023, -127, 127);
  int yMapped = map(yValue, 0, 1023, -127, 127);
  
  // Set joystick X and Y axes
  Joystick.setXAxis(xMapped);
  Joystick.setYAxis(yMapped);
  
  // Read button states (inverted because of pull-up resistors)
  int button1State = !digitalRead(button1Pin);
  int button2State = !digitalRead(button2Pin);
  
  // Set button states if they've changed
  if (button1State != lastButton1State) {
    Joystick.setButton(0, button1State);
    lastButton1State = button1State;
  }
  
  if (button2State != lastButton2State) {
    Joystick.setButton(1, button2State);
    lastButton2State = button2State;
  }
  
  // Small delay
  delay(10);
} 