/*
 * Arduino HID Keyboard Example
 * 
 * This sketch demonstrates how to use an Arduino with ATmega32U4 
 * (like Leonardo, Micro) as a keyboard HID device.
 * 
 * When a button is pressed, it will type "Hello, World!"
 * 
 * Hardware:
 * - Button connected to pin 2 and GND
 * - Arduino with native USB support (Leonardo, Micro, etc.)
 */

#include <Keyboard.h>

// Button pin
const int buttonPin = 2;
int previousButtonState = HIGH;

void setup() {
  // Initialize button pin as input with internal pull-up
  pinMode(buttonPin, INPUT_PULLUP);
  
  // Initialize keyboard
  Keyboard.begin();
}

void loop() {
  // Read the button state
  int buttonState = digitalRead(buttonPin);
  
  // Check if button state changed from HIGH to LOW (button press)
  if ((buttonState != previousButtonState) && (buttonState == LOW)) {
    // Send keystrokes
    Keyboard.println("Hello, World!");
    
    // Wait for debounce
    delay(100);
  }
  
  // Save the current button state for next comparison
  previousButtonState = buttonState;
  
  // Small delay to avoid bouncing
  delay(50);
} 