/*
 * Arduino HID Combo Device Example
 * 
 * This sketch demonstrates how to use an Arduino with ATmega32U4 
 * (like Leonardo, Micro) as both a keyboard and mouse HID device.
 * 
 * It uses potentiometers for mouse movement and buttons for 
 * keyboard keystrokes and mouse clicks.
 * 
 * Hardware:
 * - Potentiometer connected to A0 (X-axis)
 * - Potentiometer connected to A1 (Y-axis)
 * - Button connected to pin 2 and GND (mouse left click)
 * - Button connected to pin 3 and GND (keyboard 'A' key)
 * - Button connected to pin 4 and GND (keyboard 'B' key)
 * - Arduino with native USB support (Leonardo, Micro, etc.)
 */

#include <Mouse.h>
#include <Keyboard.h>

// Analog pins for mouse movement
const int xAxis = A0;
const int yAxis = A1;

// Button pins
const int mouseClickPin = 2;
const int keyboardPinA = 3;
const int keyboardPinB = 4;

// Variables for mouse movement
int range = 12;           // Output range of X or Y movement
int responseDelay = 5;    // Response delay of the mouse, in ms
int threshold = range/4;  // Threshold for mouse movement
int center = range/2;     // Center position of joystick

// Variables to store previous button states
int lastMouseButtonState = HIGH;
int lastKeyboardStateA = HIGH;
int lastKeyboardStateB = HIGH;

void setup() {
  // Initialize button pins as input with pull-up resistors
  pinMode(mouseClickPin, INPUT_PULLUP);
  pinMode(keyboardPinA, INPUT_PULLUP);
  pinMode(keyboardPinB, INPUT_PULLUP);
  
  // Initialize mouse and keyboard control
  Mouse.begin();
  Keyboard.begin();
}

void loop() {
  // ---- Mouse Control ----
  // Read the X and Y axis
  int xReading = readAxis(xAxis);
  int yReading = readAxis(yAxis);
  
  // Move the mouse
  Mouse.move(xReading, yReading, 0);

  // Read the mouse button
  int mouseButtonState = digitalRead(mouseClickPin);
  
  // Check if mouse button state changed
  if (mouseButtonState != lastMouseButtonState) {
    if (mouseButtonState == LOW) {
      Mouse.press(MOUSE_LEFT);
    } else {
      Mouse.release(MOUSE_LEFT);
    }
    lastMouseButtonState = mouseButtonState;
  }
  
  // ---- Keyboard Control ----
  // Read keyboard button A
  int keyboardStateA = digitalRead(keyboardPinA);
  
  // Check if keyboard button A state changed
  if (keyboardStateA != lastKeyboardStateA) {
    if (keyboardStateA == LOW) {
      Keyboard.press('A');
    } else {
      Keyboard.release('A');
    }
    lastKeyboardStateA = keyboardStateA;
  }
  
  // Read keyboard button B
  int keyboardStateB = digitalRead(keyboardPinB);
  
  // Check if keyboard button B state changed
  if (keyboardStateB != lastKeyboardStateB) {
    if (keyboardStateB == LOW) {
      Keyboard.press('B');
    } else {
      Keyboard.release('B');
    }
    lastKeyboardStateB = keyboardStateB;
  }
  
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