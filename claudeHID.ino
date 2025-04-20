#include <hidboot.h>
#include <usbhid.h>
#include <SPI.h>
#include <usbhub.h>
#include <Mouse.h>

// USB Host Shield setup
USB Usb;
USBHub Hub(&Usb);
HIDBoot<USB_HID_PROTOCOL_MOUSE> HidMouse(&Usb);

// Mouse button states
bool leftButtonState = false;
bool rightButtonState = false;
bool middleButtonState = false;

// Device identification
const char DEVICE_ID[] = "Arduino Leonardo with USB Host Shield";

class MouseRptParser : public MouseReportParser {
  protected:
    void OnMouseMove(MOUSEINFO *mi) {
      // Get the movement data
      int8_t x = mi->dX;
      int8_t y = mi->dY;

      // Send data over serial in a structured format
      Serial.print("M,"); // M for Move
      Serial.print(x);
      Serial.print(",");
      Serial.println(y);
      
      // Pass through the mouse movement directly
      Mouse.move(x, y, 0);
    }
    
    void OnLeftButtonUp(MOUSEINFO *mi) {
      leftButtonState = false;
      Serial.println("L,0"); // L for Left button, 0 for up
      Mouse.release(MOUSE_LEFT);
    }
    
    void OnLeftButtonDown(MOUSEINFO *mi) {
      leftButtonState = true;
      Serial.println("L,1"); // L for Left button, 1 for down
      Mouse.press(MOUSE_LEFT);
    }
    
    void OnRightButtonUp(MOUSEINFO *mi) {
      rightButtonState = false;
      Serial.println("R,0"); // R for Right button, 0 for up
      Mouse.release(MOUSE_RIGHT);
    }
    
    void OnRightButtonDown(MOUSEINFO *mi) {
      rightButtonState = true;
      Serial.println("R,1"); // R for Right button, 1 for down
      Mouse.press(MOUSE_RIGHT);
    }
    
    void OnMiddleButtonUp(MOUSEINFO *mi) {
      middleButtonState = false;
      Serial.println("N,0"); // N for Middle button, 0 for up
      Mouse.release(MOUSE_MIDDLE);
    }
    
    void OnMiddleButtonDown(MOUSEINFO *mi) {
      middleButtonState = true;
      Serial.println("N,1"); // N for Middle button, 1 for down
      Mouse.press(MOUSE_MIDDLE);
    }
};

MouseRptParser MousePrs;

void setup() {
  // Set up serial communication with the PC at 115200 baud for faster data transfer
  Serial.begin(115200);
  
  // Initialize USB Host Shield
  if (Usb.Init() == -1) {
    Serial.println("E,USB Host Shield initialization failed!"); // E for Error
    while (1); // Halt
  }
  
  Serial.println("I,USB Host Shield initialized"); // I for Info
  HidMouse.SetReportParser(0, &MousePrs);
  
  // Initialize the Mouse library
  Mouse.begin();
  
  // Send device identification on startup
  Serial.print("I,DEVICE_ID,");
  Serial.println(DEVICE_ID);
}

void loop() {
  Usb.Task();
  
  // Check if serial data is received (commands from Python)
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    
    // Process commands
    if (command == "STATUS") {
      // Send current status
      Serial.println("I,READY,USB Host Shield active");
    }
    else if (command == "VERIFY") {
      // Send verification response with device ID
      Serial.print("I,VERIFIED,");
      Serial.println(DEVICE_ID);
    }
    else if (command == "BUTTONS") {
      // Report current button states
      Serial.print("I,BUTTONS,");
      Serial.print(leftButtonState ? "1," : "0,");
      Serial.print(rightButtonState ? "1," : "0,");
      Serial.println(middleButtonState ? "1" : "0");
    }
  }
} 