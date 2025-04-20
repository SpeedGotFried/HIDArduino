import numpy as np
import threading
import time
import sys
import argparse
import ctypes
from ctypes import Structure, c_long, c_ulong, byref
from collections import deque
import math

# Define required Windows structures & types
class POINT(Structure):
    _fields_ = [("x", c_long), 
                ("y", c_long)]

# Load required DLLs
user32 = ctypes.WinDLL('user32', use_last_error=True)

# Global settings with enhanced detection parameters
SAMPLE_SIZE = 25                # Number of samples to analyze for tremor detection
SHAKE_THRESHOLD = 1.7           # Threshold for detecting shaky movement
SMOOTHING_FACTOR = 0.4          # Smoothing factor (0-1)
FREQUENCY_WINDOW = 15           # Window for frequency analysis (samples)
MIN_TREMOR_FREQUENCY = 3.0      # Minimum frequency to consider as tremor (Hz)
MAX_TREMOR_FREQUENCY = 12.0     # Maximum frequency to consider as tremor (Hz)
DIRECTION_CHANGE_THRESHOLD = 0.4 # Threshold for direction changes
STD_DEV_THRESHOLD = 0.75        # Threshold for standard deviation variance
JITTER_THRESHOLD = 2.0          # Threshold for detecting jitter
ADAPTIVE_SMOOTHING = True       # Enable adaptive smoothing based on tremor intensity

# Global state
position_history = deque(maxlen=SAMPLE_SIZE)  # Store actual positions
delta_history = deque(maxlen=SAMPLE_SIZE)     # Store movement deltas
timestamp_history = deque(maxlen=SAMPLE_SIZE) # Store timestamps for frequency analysis
tremor_detected = False
tremor_type = "None"            # Store the type of tremor detected
tremor_intensity = 0.0          # Store the intensity of tremor (0-1)
stabilization_active = True
running = True
lock = threading.Lock()

# Last positions for smoothing
last_x = 0
last_y = 0
last_real_x = 0
last_real_y = 0
last_time = time.time()

def calculate_magnitude(x, y):
    """Calculate the magnitude of movement vector."""
    return np.sqrt(x**2 + y**2)

def calculate_frequency():
    """Estimate frequency of movement from timestamps."""
    if len(timestamp_history) < FREQUENCY_WINDOW:
        return 0
    
    # Get the last n timestamps
    recent_times = list(timestamp_history)[-FREQUENCY_WINDOW:]
    
    # Calculate time intervals between consecutive movements
    intervals = [recent_times[i] - recent_times[i-1] for i in range(1, len(recent_times))]
    
    if not intervals:
        return 0
    
    # Calculate average time between movements
    avg_interval = np.mean(intervals)
    
    # Prevent division by zero
    if avg_interval == 0:
        return 0
    
    # Convert to frequency (Hz)
    frequency = 1.0 / avg_interval
    
    return frequency

def calculate_jitter(positions):
    """Calculate the jitter (quick, tiny movements)."""
    if len(positions) < 3:
        return 0
    
    # Calculate the second derivative (change in movement rate)
    first_derivs = []
    for i in range(1, len(positions)):
        dx1 = positions[i][0] - positions[i-1][0]
        dy1 = positions[i][1] - positions[i-1][1]
        first_derivs.append((dx1, dy1))
    
    second_derivs = []
    for i in range(1, len(first_derivs)):
        dx2 = first_derivs[i][0] - first_derivs[i-1][0]
        dy2 = first_derivs[i][1] - first_derivs[i-1][1]
        second_derivs.append(calculate_magnitude(dx2, dy2))
    
    # Return average magnitude of second derivatives
    return np.mean(second_derivs) if second_derivs else 0

def detect_tremor(dx, dy, current_x, current_y):
    """Enhanced tremor detection algorithm."""
    global delta_history, position_history, timestamp_history, tremor_type, tremor_intensity
    
    now = time.time()
    
    # Store movement data
    delta_history.append((dx, dy))
    position_history.append((current_x, current_y))
    timestamp_history.append(now)
    
    # Not enough data yet
    if len(delta_history) < SAMPLE_SIZE // 2:
        return False
    
    # Calculate current magnitude
    current_magnitude = calculate_magnitude(dx, dy)
    
    # Calculate statistics of recent movements
    deltas = list(delta_history)
    magnitudes = [calculate_magnitude(d[0], d[1]) for d in deltas]
    avg_magnitude = np.mean(magnitudes)
    std_magnitude = np.std(magnitudes)
    
    # Calculate directional changes
    directions = []
    for i in range(1, len(deltas)):
        prev_x, prev_y = deltas[i-1]
        curr_x, curr_y = deltas[i]
        
        # Calculate direction change (dot product will be negative if direction changes)
        if (prev_x != 0 or prev_y != 0) and (curr_x != 0 or curr_y != 0):
            # Calculate the cosine of the angle between vectors
            dot_product = prev_x * curr_x + prev_y * curr_y
            magnitude_product = calculate_magnitude(prev_x, prev_y) * calculate_magnitude(curr_x, curr_y)
            
            if magnitude_product != 0:
                cos_angle = dot_product / magnitude_product
                directions.append(cos_angle)
    
    # Count sudden direction changes (when cos angle is negative or small)
    direction_changes = sum(1 for d in directions if d < 0)
    direction_change_ratio = direction_changes / len(directions) if directions else 0
    
    # Calculate movement frequency
    frequency = calculate_frequency()
    
    # Calculate jitter (rapid tiny movements)
    jitter = calculate_jitter(list(position_history))
    
    # Coefficient of variation (measure of inconsistency in movement size)
    cv = std_magnitude / avg_magnitude if avg_magnitude > 0 else 0
    
    # Check for different types of tremors
    frequency_tremor = (MIN_TREMOR_FREQUENCY <= frequency <= MAX_TREMOR_FREQUENCY)
    directional_tremor = (direction_change_ratio > DIRECTION_CHANGE_THRESHOLD)
    magnitude_tremor = (current_magnitude > avg_magnitude * SHAKE_THRESHOLD)
    jitter_tremor = (jitter > JITTER_THRESHOLD)
    variance_tremor = (cv > STD_DEV_THRESHOLD)
    
    # Combine tremor detections with weights
    tremor_scores = {
        "Frequency": 1.0 if frequency_tremor else 0.0,
        "Directional": 1.0 if directional_tremor else 0.0,
        "Magnitude": 1.0 if magnitude_tremor else 0.0,
        "Jitter": 1.0 if jitter_tremor else 0.0,
        "Variance": 1.0 if variance_tremor else 0.0
    }
    
    # Calculate overall tremor score
    tremor_score = sum(tremor_scores.values()) / 5.0
    tremor_detected = tremor_score > 0.3  # Require at least 2 criteria to be met
    
    # Set tremor intensity based on the score
    tremor_intensity = tremor_score
    
    # Determine tremor type for reporting
    if tremor_detected:
        detected_types = [t for t, v in tremor_scores.items() if v > 0]
        tremor_type = "+".join(detected_types)
    else:
        tremor_type = "None"
    
    return tremor_detected

def apply_adaptive_smoothing(x, y):
    """Apply adaptive smoothing based on tremor intensity."""
    global last_x, last_y, tremor_intensity
    
    # Adjust smoothing factor based on tremor intensity
    if ADAPTIVE_SMOOTHING:
        # More intense tremor = stronger smoothing (lower weight to current position)
        adaptive_factor = max(0.1, SMOOTHING_FACTOR * (1.0 - tremor_intensity))
    else:
        adaptive_factor = SMOOTHING_FACTOR
    
    # Apply exponential smoothing
    filtered_x = adaptive_factor * x + (1 - adaptive_factor) * last_x
    filtered_y = adaptive_factor * y + (1 - adaptive_factor) * last_y
    
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
    global tremor_detected, last_real_x, last_real_y, last_time
    
    # Initialize last position
    last_real_x, last_real_y = get_cursor_pos()
    last_x, last_y = last_real_x, last_real_y
    last_time = time.time()
    
    try:
        while running:
            # Get current cursor position
            current_x, current_y = get_cursor_pos()
            now = time.time()
            
            # Calculate movement delta
            dx = current_x - last_real_x
            dy = current_y - last_real_y
            
            # Update last real position
            last_real_x, last_real_y = current_x, current_y
            
            # Only process if there's actual movement and stabilization is active
            if (dx != 0 or dy != 0) and stabilization_active:
                with lock:
                    # Detect tremor with enhanced algorithm
                    tremor_detected = detect_tremor(dx, dy, current_x, current_y)
                    
                    # Apply smoothing if tremor detected
                    if tremor_detected:
                        # Get new smoothed position with adaptive smoothing
                        new_x, new_y = apply_adaptive_smoothing(current_x, current_y)
                        
                        # Set new cursor position
                        set_cursor_pos(new_x, new_y)
                        
                        # Update to use the new position as reference
                        last_real_x, last_real_y = new_x, new_y
            
            # Adaptive polling rate - sleep less if movement is detected
            sleep_time = 0.002 if dx != 0 or dy != 0 else 0.005
            time.sleep(sleep_time)
    
    except Exception as e:
        print(f"Error in mouse monitor: {e}")

def status_monitor():
    """Display tremor detection status periodically."""
    global tremor_detected, stabilization_active, tremor_type, tremor_intensity
    
    try:
        while running:
            with lock:
                status = f"TREMOR: {tremor_type} ({int(tremor_intensity*100)}%)" if tremor_detected else "Normal movement"
                mode = "ACTIVE" if stabilization_active else "DISABLED"
                
                # Include detected parameters
                if tremor_detected:
                    freq = calculate_frequency()
                    freq_info = f"Freq: {freq:.1f}Hz"
                else:
                    freq_info = ""
            
            sys.stdout.write(f"\rStatus: {status} | {freq_info} | Stabilization: {mode}" + " "*10)
            sys.stdout.flush()
            time.sleep(0.2)
    
    except KeyboardInterrupt:
        pass

def toggle_stabilization():
    """Toggle the stabilization on or off."""
    global stabilization_active
    
    with lock:
        stabilization_active = not stabilization_active
    
    print(f"\nStabilization {'ENABLED' if stabilization_active else 'DISABLED'}")

def main():
    global SHAKE_THRESHOLD, SMOOTHING_FACTOR, SAMPLE_SIZE, FREQUENCY_WINDOW
    global MIN_TREMOR_FREQUENCY, MAX_TREMOR_FREQUENCY, DIRECTION_CHANGE_THRESHOLD
    global STD_DEV_THRESHOLD, JITTER_THRESHOLD, ADAPTIVE_SMOOTHING
    global running
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Enhanced Tremor Filter")
    parser.add_argument('--threshold', type=float, default=1.7, 
                        help='Magnitude threshold (default: 1.7)')
    parser.add_argument('--smoothing', type=float, default=0.4, 
                        help='Smoothing factor (default: 0.4)')
    parser.add_argument('--samples', type=int, default=25, 
                        help='Sample size (default: 25)')
    parser.add_argument('--min-freq', type=float, default=3.0, 
                        help='Minimum tremor frequency in Hz (default: 3.0)')
    parser.add_argument('--max-freq', type=float, default=12.0, 
                        help='Maximum tremor frequency in Hz (default: 12.0)')
    parser.add_argument('--direction-threshold', type=float, default=0.4, 
                        help='Direction change threshold (default: 0.4)')
    parser.add_argument('--std-threshold', type=float, default=0.75, 
                        help='Standard deviation threshold (default: 0.75)')
    parser.add_argument('--jitter-threshold', type=float, default=2.0, 
                        help='Jitter threshold (default: 2.0)')
    parser.add_argument('--adaptive', type=bool, default=True, 
                        help='Enable adaptive smoothing (default: True)')
    
    args = parser.parse_args()
    
    # Update parameters from command line
    SHAKE_THRESHOLD = args.threshold
    SMOOTHING_FACTOR = args.smoothing
    SAMPLE_SIZE = args.samples
    MIN_TREMOR_FREQUENCY = args.min_freq
    MAX_TREMOR_FREQUENCY = args.max_freq
    DIRECTION_CHANGE_THRESHOLD = args.direction_threshold
    STD_DEV_THRESHOLD = args.std_threshold
    JITTER_THRESHOLD = args.jitter_threshold
    ADAPTIVE_SMOOTHING = args.adaptive
    
    print("Enhanced Tremor Filter v2.0")
    print("===========================")
    print(f"Magnitude Threshold: {SHAKE_THRESHOLD}")
    print(f"Smoothing Factor: {SMOOTHING_FACTOR}")
    print(f"Sample Size: {SAMPLE_SIZE}")
    print(f"Tremor Frequency Range: {MIN_TREMOR_FREQUENCY}-{MAX_TREMOR_FREQUENCY} Hz")
    print(f"Direction Change Threshold: {DIRECTION_CHANGE_THRESHOLD}")
    print(f"Standard Deviation Threshold: {STD_DEV_THRESHOLD}")
    print(f"Jitter Threshold: {JITTER_THRESHOLD}")
    print(f"Adaptive Smoothing: {'Enabled' if ADAPTIVE_SMOOTHING else 'Disabled'}")
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