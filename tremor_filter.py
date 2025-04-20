import serial
import serial.tools.list_ports
import time
import sys
import numpy as np
import pyautogui
import threading
import argparse
from collections import deque

# Global settings
SAMPLE_SIZE = 20  # Number of samples to analyze for tremor detection
SHAKE_THRESHOLD = 1.7  # Threshold for detecting shaky movement
SMOOTHING_FACTOR = 0.4  # Smoothing factor (0-1)
SERIAL_TIMEOUT = 0.1  # Timeout for serial operations

# Global state
mouse_history = deque(maxlen=SAMPLE_SIZE)
tremor_detected = False
stabilization_active = True
serial_connected = False
arduino_verified = False

# Last filtered position
last_x = 0
last_y = 0

# Create a lock for safe access to shared resources
lock = threading.Lock()

def calculate_magnitude(x, y):
    """Calculate the magnitude of movement vector."""
    return np.sqrt(x**2 + y**2)

def detect_tremor(x, y):
    """Determine if movement exhibits tremor-like behavior."""
    global mouse_history
    
    # Add current movement to history
    mouse_history.append((x, y))
    
    # Not enough data yet
    if len(mouse_history) < SAMPLE_SIZE // 2:
        return False
    
    # Calculate current magnitude
    current_magnitude = calculate_magnitude(x, y)
    
    # Calculate statistics of recent movements
    magnitudes = [calculate_magnitude(px, py) for px, py in mouse_history]
    avg_magnitude = np.mean(magnitudes)
    std_magnitude = np.std(magnitudes)
    
    # Calculate directional changes
    directions = []
    for i in range(1, len(mouse_history)):
        prev_x, prev_y = mouse_history[i-1]
        curr_x, curr_y = mouse_history[i]
        
        # Calculate direction change (dot product will be negative if direction changes)
        if prev_x != 0 or prev_y != 0:
            dot_product = prev_x * curr_x + prev_y * curr_y
            directions.append(dot_product)
    
    # Count direction changes (negative dot products indicate direction change)
    direction_changes = sum(1 for d in directions if d < 0)
    
    # Tremor detection criteria:
    # 1. Current magnitude is high relative to average
    # 2. Many direction changes in short time (characteristic of tremor)
    # 3. High standard deviation in movement magnitudes
    
    is_tremor = (
        (current_magnitude > avg_magnitude * SHAKE_THRESHOLD) or
        (direction_changes > len(directions) * 0.4) or
        (std_magnitude > avg_magnitude * 0.8)
    )
    
    return is_tremor

def apply_smoothing(x, y):
    """Apply smoothing filter to tremorous movement."""
    global last_x, last_y
    
    # Apply exponential smoothing
    filtered_x = SMOOTHING_FACTOR * x + (1 - SMOOTHING_FACTOR) * last_x
    filtered_y = SMOOTHING_FACTOR * y + (1 - SMOOTHING_FACTOR) * last_y
    
    # Update last known position
    last_x = filtered_x
    last_y = filtered_y
    
    return filtered_x, filtered_y

def list_all_ports():
    """List all available COM ports."""
    ports = serial.tools.list_ports.comports()
    print("\nAvailable COM ports:")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device} - {port.description}")
    print()

def process_data(ser):
    """Process incoming data from the Arduino."""
    global tremor_detected, arduino_verified
    
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue
                
                parts = line.split(',')
                
                # Process mouse movement
                if parts[0] == 'M' and len(parts) >= 3:
                    try:
                        x = int(parts[1])
                        y = int(parts[2])
                        
                        with lock:
                            # Detect tremor
                            tremor_detected = detect_tremor(x, y)
                            
                            # Apply filters if tremors detected and stabilization is active
                            if tremor_detected and stabilization_active:
                                x, y = apply_smoothing(x, y)
                            
                            # Move the mouse cursor (if x and y are nonzero)
                            if x != 0 or y != 0:
                                pyautogui.moveRel(int(x), int(y), _pause=False)
                    
                    except ValueError:
                        print(f"Error parsing movement data: {line}")
                
                # Process button press/release
                elif parts[0] in ['L', 'R', 'N'] and len(parts) >= 2:
                    button_state = parts[1] == '1'  # 1 = pressed, 0 = released
                    
                    # Map to pyautogui's button names
                    button_map = {
                        'L': 'left',
                        'R': 'right',
                        'N': 'middle'
                    }
                    
                    button = button_map[parts[0]]
                    
                    if button_state:
                        pyautogui.mouseDown(button=button, _pause=False)
                    else:
                        pyautogui.mouseUp(button=button, _pause=False)
                
                # Process information messages
                elif parts[0] == 'I':
                    print(f"Info: {','.join(parts[1:])}")
                    # Check for identification message
                    if "USB Host Shield" in line:
                        arduino_verified = True
                
                # Process error messages
                elif parts[0] == 'E':
                    print(f"Error from Arduino: {','.join(parts[1:])}")
    
    except KeyboardInterrupt:
        print("Data processing interrupted")
    except Exception as e:
        print(f"Error in data processing: {e}")

def status_monitor():
    """Display tremor detection status periodically."""
    global tremor_detected, serial_connected, stabilization_active
    
    try:
        while serial_connected:
            with lock:
                status = "TREMOR DETECTED - Stabilizing" if tremor_detected else "Normal movement"
                mode = "ACTIVE" if stabilization_active else "DISABLED"
            
            print(f"Status: {status} | Stabilization: {mode}", end='\r')
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        pass

def main():
    global stabilization_active, serial_connected
    
    parser = argparse.ArgumentParser(description="Mouse Tremor Filter")
    parser.add_argument('--port', default="COM14", help='Serial port for Arduino (required)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate for serial communication')
    parser.add_argument('--list', action='store_true', help='List all available COM ports and exit')
    args = parser.parse_args()
    
    # List all ports if requested
    if args.list:
        list_all_ports()
        return
    
    # Use the specified port
    port = args.port
    print(f"Connecting to Arduino on {port} at {args.baud} baud...")
    
    # Connect to the Arduino
    try:
        ser = serial.Serial(port, args.baud, timeout=SERIAL_TIMEOUT)
        time.sleep(2)  # Allow time for Arduino to reset
        serial_connected = True
        print(f"Connected to {port}!")
        
        # Start data processing thread
        data_thread = threading.Thread(target=process_data, args=(ser,))
        data_thread.daemon = True
        data_thread.start()
        
        # Start status monitor thread
        status_thread = threading.Thread(target=status_monitor)
        status_thread.daemon = True
        status_thread.start()
        
        print("\nTremor Filter Running")
        print("Press 'q' to quit, 's' to toggle stabilization")
        
        # Main loop for user commands
        while True:
            key = input()
            
            if key.lower() == 'q':
                print("Shutting down...")
                break
            
            elif key.lower() == 's':
                with lock:
                    stabilization_active = not stabilization_active
                print(f"Stabilization {'ENABLED' if stabilization_active else 'DISABLED'}")
    
    except serial.SerialException as e:
        print(f"Error connecting to serial port: {e}")
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        serial_connected = False
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    print("Mouse Tremor Filter v1.0")
    print("========================")
    # Set up PyAutoGUI
    pyautogui.FAILSAFE = False
    main() 