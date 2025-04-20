import ctypes
from ctypes import windll, wintypes, Structure, CFUNCTYPE, POINTER, byref
import threading
import numpy as np
import time
import sys
import argparse
from collections import deque

# Windows API constants
WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208

# Load libraries directly 
user32 = windll.user32
kernel32 = windll.kernel32

# Define required Windows structures
class POINT(Structure):
    _fields_ = [("x", wintypes.LONG),
                ("y", wintypes.LONG)]

class MSLLHOOKSTRUCT(Structure):
    _fields_ = [("pt", POINT),
                ("mouseData", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG)]

# Define function prototypes
user32.SetWindowsHookExA.restype = wintypes.HHOOK
user32.SetWindowsHookExA.argtypes = [wintypes.INT, wintypes.HANDLE, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = wintypes.LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetMessageW.argtypes = [POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetCursorPos.argtypes = [POINTER(POINT)]

# Define the hook callback
HOOKPROC = CFUNCTYPE(wintypes.LRESULT, wintypes.INT, wintypes.WPARAM, POINTER(MSLLHOOKSTRUCT))

# Global settings
SAMPLE_SIZE = 20  # Number of samples to analyze for tremor detection
SHAKE_THRESHOLD = 1.7  # Threshold for detecting shaky movement
SMOOTHING_FACTOR = 0.4  # Smoothing factor (0-1)

# Global state
mouse_history = deque(maxlen=SAMPLE_SIZE)
tremor_detected = False
stabilization_active = True
hook_handle = None
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

def mouse_callback(n_code, w_param, l_param):
    """Callback function for mouse hook."""
    global tremor_detected, last_real_x, last_real_y
    
    if n_code < 0:
        return user32.CallNextHookEx(hook_handle, n_code, w_param, l_param)
    
    if w_param == WM_MOUSEMOVE and stabilization_active:
        # Get current cursor position
        current_x, current_y = get_cursor_pos()
        
        # Calculate movement delta
        dx = current_x - last_real_x
        dy = current_y - last_real_y
        
        # Update last real position
        last_real_x = current_x
        last_real_y = current_y
        
        # Only process if there's actual movement
        if dx != 0 or dy != 0:
            with lock:
                # Detect tremor
                tremor_detected = detect_tremor(dx, dy)
                
                # Apply smoothing if tremor detected
                if tremor_detected:
                    # Get new smoothed position
                    new_x, new_y = apply_smoothing(current_x, current_y)
                    
                    # Set new cursor position
                    set_cursor_pos(new_x, new_y)
                    
                    # We've handled this movement, prevent further processing
                    return 1
    
    # Let Windows process other mouse events normally
    return user32.CallNextHookEx(hook_handle, n_code, w_param, l_param)

def start_hook():
    """Set up and start the mouse hook."""
    global hook_handle, last_real_x, last_real_y
    
    # Initialize last position
    last_real_x, last_real_y = get_cursor_pos()
    
    # Create callback function
    callback = HOOKPROC(mouse_callback)
    
    # Set the hook
    try:
        hook_handle = user32.SetWindowsHookExA(
            WH_MOUSE_LL,
            callback,
            kernel32.GetModuleHandleA(None),
            0
        )
        
        if not hook_handle:
            error_code = kernel32.GetLastError()
            raise ctypes.WinError(error_code)
        
        print("Mouse hook successfully installed")
        
        # Keep reference to callback to prevent garbage collection
        start_hook.callback = callback
        
        # Create message loop
        msg = wintypes.MSG()
        while user32.GetMessageW(byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
    
    except Exception as e:
        print(f"Error setting up hook: {e}")
        raise

def stop_hook():
    """Remove the mouse hook."""
    global hook_handle
    
    if hook_handle:
        success = user32.UnhookWindowsHookEx(hook_handle)
        if success:
            print("Mouse hook successfully removed")
        else:
            print("Failed to remove mouse hook")
        hook_handle = None

def status_monitor():
    """Display tremor detection status periodically."""
    global tremor_detected, stabilization_active
    
    try:
        while True:
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
    global SHAKE_THRESHOLD, SMOOTHING_FACTOR, SAMPLE_SIZE
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Windows Mouse Tremor Filter")
    parser.add_argument('--threshold', type=float, default=1.7, help='Tremor detection threshold (default: 1.7)')
    parser.add_argument('--smoothing', type=float, default=0.4, help='Smoothing factor (default: 0.4)')
    parser.add_argument('--samples', type=int, default=20, help='Sample size for tremor detection (default: 20)')
    args = parser.parse_args()
    
    # Update parameters from command line
    SHAKE_THRESHOLD = args.threshold
    SMOOTHING_FACTOR = args.smoothing
    SAMPLE_SIZE = args.samples
    
    print("Windows Mouse Tremor Filter v1.0")
    print("================================")
    print(f"Tremor Threshold: {SHAKE_THRESHOLD}")
    print(f"Smoothing Factor: {SMOOTHING_FACTOR}")
    print(f"Sample Size: {SAMPLE_SIZE}")
    print("Starting stabilization system...")
    
    # Start status monitor in a background thread
    status_thread = threading.Thread(target=status_monitor)
    status_thread.daemon = True
    status_thread.start()
    
    # Create keyboard listener thread for commands
    def key_monitor():
        print("\nPress 'q' to quit, 's' to toggle stabilization")
        while True:
            try:
                key = input()
                if key.lower() == 'q':
                    print("\nShutting down...")
                    stop_hook()
                    sys.exit(0)
                elif key.lower() == 's':
                    toggle_stabilization()
            except EOFError:
                time.sleep(0.1)
    
    key_thread = threading.Thread(target=key_monitor)
    key_thread.daemon = True
    key_thread.start()
    
    try:
        # Start the mouse hook
        start_hook()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_hook()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        print("Falling back to the pynput version...")
        print("Please run 'python mouse_filter.py' instead.") 