import numpy as np
import threading
import time
import sys
import argparse
import ctypes
from ctypes import Structure, c_long, c_ulong, byref
from collections import deque

# Define required Windows structures & types
class POINT(Structure):
    _fields_ = [("x", c_long), 
                ("y", c_long)]

# Load required DLLs
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Global settings
SAMPLE_SIZE = 20  # Number of samples to analyze for tremor detection
SHAKE_THRESHOLD = 2.5  # Threshold for detecting shaky movement
SMOOTHING_FACTOR = 0.8  # Smoothing factor (0-1)

# Global state
mouse_history = deque(maxlen=SAMPLE_SIZE)
tremor_detected = False
stabilization_active = True
running = True
lock = threading.Lock()

# Last positions for smoothing
last_x = 0
last_y = 0
last_real_x = 0
last_real_y = 0

def calculate_magnitude(x, y):
    """Calculate the magnitude of movement vector."""
    return np.sqrt(x**2 + y**2)

def detect_tremor(dx, dy):
    """Determine if movement exhibits tremor-like behavior."""
    global mouse_history
    
    # Add current movement to history
    mouse_history.append((dx, dy))
    
    # Not enough data yet
    if len(mouse_history) < SAMPLE_SIZE // 2:
        return False
    
    # Calculate current magnitude
    current_magnitude = calculate_magnitude(dx, dy)
    
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
    """Apply exponential smoothing to coordinates."""
    global last_x, last_y
    
    # Apply exponential smoothing
    filtered_x = SMOOTHING_FACTOR * x + (1 - SMOOTHING_FACTOR) * last_x
    filtered_y = SMOOTHING_FACTOR * y + (1 - SMOOTHING_FACTOR) * last_y
    
    # Update last smoothed position
    last_x = filtered_x
    last_y = filtered_y
    
    return int(filtered_x), int(filtered_y)

def get_cursor_pos():
    """Get current cursor position."""
    point = POINT()
    user32.GetCursorPos(byref(point))
    return point.x, point.y

def set_cursor_pos(x, y):
    """Set cursor position."""
    user32.SetCursorPos(x, y)

def mouse_monitor():
    """Monitor mouse movements using polling."""
    global tremor_detected, last_real_x, last_real_y
    
    # Initialize last position
    last_real_x, last_real_y = get_cursor_pos()
    last_x, last_y = last_real_x, last_real_y
    
    try:
        while running:
            # Get current cursor position
            current_x, current_y = get_cursor_pos()
            
            # Calculate movement delta
            dx = current_x - last_real_x
            dy = current_y - last_real_y
            
            # Update last real position
            last_real_x, last_real_y = current_x, current_y
            
            # Only process if there's actual movement and stabilization is active
            if (dx != 0 or dy != 0) and stabilization_active:
                with lock:
                    # Detect tremor
                    tremor_detected = detect_tremor(dx, dy)
                    
                    # Apply smoothing if tremor detected
                    if tremor_detected:
                        # Get new smoothed position
                        new_x, new_y = apply_smoothing(current_x, current_y)
                        
                        # Set new cursor position
                        set_cursor_pos(new_x, new_y)
                        
                        # Update to use the new position as reference
                        last_real_x, last_real_y = new_x, new_y
            
            # Short sleep to prevent CPU overuse
            time.sleep(0.005)  # 5ms polling interval
    
    except Exception as e:
        print(f"Error in mouse monitor: {e}")

def status_monitor():
    """Display tremor detection status periodically."""
    global tremor_detected, stabilization_active
    
    try:
        while running:
            with lock:
                status = "TREMOR DETECTED - Stabilizing" if tremor_detected else "Normal movement"
                mode = "ACTIVE" if stabilization_active else "DISABLED"
            
            sys.stdout.write(f"\rStatus: {status} | Stabilization: {mode}")
            sys.stdout.flush()
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        pass

def toggle_stabilization():
    """Toggle the stabilization on or off."""
    global stabilization_active
    
    with lock:
        stabilization_active = not stabilization_active
    
    print(f"\nStabilization {'ENABLED' if stabilization_active else 'DISABLED'}")

def main():
    global SHAKE_THRESHOLD, SMOOTHING_FACTOR, SAMPLE_SIZE, running
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple Windows Mouse Tremor Filter")
    parser.add_argument('--threshold', type=float, default=1.7, help='Tremor detection threshold (default: 1.7)')
    parser.add_argument('--smoothing', type=float, default=0.4, help='Smoothing factor (default: 0.4)')
    parser.add_argument('--samples', type=int, default=20, help='Sample size for tremor detection (default: 20)')
    args = parser.parse_args()
    
    # Update parameters from command line
    SHAKE_THRESHOLD = args.threshold
    SMOOTHING_FACTOR = args.smoothing
    SAMPLE_SIZE = args.samples
    
    print("Simple Windows Mouse Tremor Filter v1.0")
    print("======================================")
    print(f"Tremor Threshold: {SHAKE_THRESHOLD}")
    print(f"Smoothing Factor: {SMOOTHING_FACTOR}")
    print(f"Sample Size: {SAMPLE_SIZE}")
    print("Starting stabilization system...")
    
    # Start mouse monitor in a background thread
    mouse_thread = threading.Thread(target=mouse_monitor)
    mouse_thread.daemon = True
    mouse_thread.start()
    
    # Start status monitor in a background thread
    status_thread = threading.Thread(target=status_monitor)
    status_thread.daemon = True
    status_thread.start()
    
    # Main thread handles keyboard input
    print("\nPress 'q' to quit, 's' to toggle stabilization")
    try:
        while True:
            key = input().lower()
            if key == 'q':
                print("\nShutting down...")
                running = False
                break
            elif key == 's':
                toggle_stabilization()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        running = False

if __name__ == "__main__":
    main() 