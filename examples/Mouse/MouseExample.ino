/*
 * Arduino HID Mouse Example
 * 
 * This sketch demonstrates how to use an Arduino with ATmega32U4 
 * (like Leonardo, Micro) as a mouse HID device.
 * 
 * It uses two potentiometers to control the mouse X and Y movement,
 * and a button to control left mouse click.
 * 
 * Hardware:
 * - Potentiometer connected to A0 (X-axis)
 * - Potentiometer connected to A1 (Y-axis)
 * - Button connected to pin 2 and GND (mouse click)
 * - Arduino with native USB support (Leonardo, Micro, etc.)
 */

#include <Mouse.h>

// Analog pins for potentiometers
const int xAxis = A0;
const int yAxis = A1;

// Button pin for mouse click
const int mouseButton = 2;

// Variables for mouse movement
int range = 12;           // Output range of X or Y movement
int responseDelay = 5;    // Response delay of the mouse, in ms
int threshold = range/4;  // Threshold for mouse movement
int center = range/2;     // Center position of joystick

// Previous state of the button
int previousButtonState = HIGH;

void setup() {
  // Initialize the button pin as input with pull-up resistor
  pinMode(mouseButton, INPUT_PULLUP);
  
  // Initialize mouse control
  Mouse.begin();
}

void loop() {
  // Read the X and Y axis
  int xReading = readAxis(xAxis);
  int yReading = readAxis(yAxis);
  
  // Calculate mouse movement
  Mouse.move(xReading, yReading, 0);

  // Read the mouse button and click if pressed
  int buttonState = digitalRead(mouseButton);
  
  // Check if button state changed from HIGH to LOW (button press)
  if ((buttonState != previousButtonState) && (buttonState == LOW)) {
    Mouse.press(MOUSE_LEFT);
  } 
  // Check if button state changed from LOW to HIGH (button release)
  else if ((buttonState != previousButtonState) && (buttonState == HIGH)) {
    Mouse.release(MOUSE_LEFT);
  }
  
  // Save button state for next comparison
  previousButtonState = buttonState;

  // Small delay
  delay(responseDelay);
}

/*
 * Function to read the analog input and convert it to mouse movement
 */
int readAxis(int thisAxis) {
  // Read the analog input
  int reading = analogRead(thisAxis);
  
  // Map reading from the analog input range to the output range
  reading = map(reading, 0, 1023, 0, range);
  
  // If the reading is within the threshold, return 0
  int distance = reading - center;
  if (abs(distance) < threshold) {
    distance = 0;
  }
  
  // Return the distance for this axis
  return distance;
} 