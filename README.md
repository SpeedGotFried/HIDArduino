# Mouse Tremor Filtering System

A system to help people with tremors (such as those with Parkinson's disease) use a computer mouse more effectively by filtering out involuntary movements while preserving intentional control.

## Overview

This system consists of two parts:

1. **Arduino Leonardo with USB Host Shield**: Acts as a pass-through for a USB mouse, sending all mouse movement and button data to the computer both through HID (normal mouse function) and over serial (for analysis).

2. **Python Tremor Filter**: Analyzes the mouse movements received via serial connection, detects tremors, and applies smoothing algorithms when tremors are detected.

With this approach, the mouse will work normally even without the Python program running, but when the Python program is active, it will provide additional filtering of tremors.

## Hardware Requirements

- Arduino Leonardo (or compatible board with USB HID support)
- USB Host Shield 2.0
- USB Mouse

## Software Requirements

### Arduino
- [Arduino IDE](https://www.arduino.cc/en/software)
- [USB Host Shield 2.0 Library](https://github.com/felis/USB_Host_Shield_2.0)

### Python
- Python 3.6+
- Required packages:
  - pyserial
  - numpy
  - pyautogui

## Setup Instructions

### 1. Hardware Setup

1. Connect the USB Host Shield to your Arduino Leonardo
2. Connect the Arduino Leonardo to your computer via USB
3. Connect the USB mouse to the USB Host Shield

### 2. Arduino Setup

1. Install the Arduino IDE
2. Install the USB Host Shield 2.0 Library (Sketch → Include Library → Manage Libraries...)
3. Open the `claudeHID.ino` sketch
4. Select "Arduino Leonardo" from the Tools → Board menu
5. Select the correct port from Tools → Port
6. Upload the sketch to your Arduino

### 3. Python Setup

1. Install Python 3.6 or later
2. Install required packages:
   ```
   pip install pyserial numpy pyautogui
   ```
3. Run the Python script:
   ```
   python tremor_filter.py
   ```
   
   The script will automatically try to find the Arduino. If it can't find it automatically, it will display a list of available ports for you to choose from.

### 4. COM Port Selection and Device Verification

The Python script has been enhanced to ensure it only processes inputs from the Arduino's mouse:

1. **Automatic port detection**: The script will scan all available COM ports and try to identify the Arduino
2. **Manual port selection**: If automatic detection fails, it will display a list of all available ports and prompt you to select one
3. **Device verification**: The script communicates with the device to confirm it's the Arduino with USB Host Shield

If you prefer to specify the port directly, use the `--port` argument:
```
python tremor_filter.py --port COM3  # Replace COM3 with your port
```

To list all available COM ports without starting the application:
```
python tremor_filter.py --list
```

To bypass verification (not recommended):
```
python tremor_filter.py --force
```

## Usage

1. Connect all hardware as described in the setup instructions
2. Upload the Arduino sketch
3. Run the Python script
4. The mouse will work normally, but movements will be smoothed when tremors are detected

### Commands

While the Python script is running:
- Press `s` to toggle stabilization on/off
- Press `q` to quit the program
- Press `v` to manually verify Arduino connection

## How It Works

### Tremor Detection

The system detects tremors using multiple criteria:
- Magnitude of movement relative to average recent movements
- Frequency of directional changes
- Variance in movement magnitudes

These are characteristic of tremors, which typically involve rapid back-and-forth movements.

### Filtering Method

When tremors are detected, the system applies exponential smoothing to the mouse movements:
- Recent mouse positions are given higher weight
- Older positions are given lower weight
- This creates a smooth, averaged movement that filters out rapid changes

### Device Verification

To ensure the system is only filtering inputs from the Arduino-connected mouse (and not interfering with other mice):
1. The Arduino transmits a unique device identifier
2. The Python script verifies this identifier before processing inputs
3. The script monitors for correct protocol format from the Arduino
4. The status display shows whether the device is verified

## Adjustable Parameters

In the Python script, you can adjust these parameters to fine-tune the system:

- `SAMPLE_SIZE`: Number of samples to analyze (higher = more history, but slower to adapt)
- `SHAKE_THRESHOLD`: Sensitivity of tremor detection (higher = less sensitive)
- `SMOOTHING_FACTOR`: Amount of smoothing (lower = more aggressive smoothing)

## Troubleshooting

### Arduino Not Recognized

Make sure:
- You've selected the correct board in the Arduino IDE
- The Arduino is connected to your computer
- You've installed any necessary drivers for your Arduino

### Python Can't Find Arduino

- Use the `--list` option to see all available ports
- Try specifying the port manually using the `--port` argument
- Make sure the Arduino is properly connected and the sketch is running
- Check if the port is being used by another application

### Mouse Not Working

- Check that all connections are secure
- Verify the USB Host Shield is properly connected to the Arduino
- Try a different USB mouse
- Check the serial output for any error messages

### Verification Failed

If the device verification fails:
- Ensure the Arduino is running the correct sketch
- Check that the serial connection is stable
- Try restarting both the Arduino and Python script
- As a last resort, use the `--force` option to bypass verification

## License

This project is open source and available under the MIT License.

## Credits

Created as an assistive technology project to help people with tremors use computers more effectively. #   H I D A r d u i n o  
 