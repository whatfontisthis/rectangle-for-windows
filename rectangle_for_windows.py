import keyboard
import win32gui
import win32con
import win32api
import sys
import ctypes
import logging
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Global flag to manage the program's running state
running = True


def log_action(action):
    logging.info(action)


# Function to create a system tray icon
def create_image():
    image = Image.new("RGB", (64, 64), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=(0, 0, 0))
    return image


def quit_app(icon, item):
    global running
    running = False  # Stop the main loop
    log_action("Exiting app via tray icon.")
    icon.stop()


# Get the handle of the active window
def get_active_window():
    return win32gui.GetForegroundWindow()


# Snap the active window to a specific screen position
def snap_window(direction):
    hwnd = get_active_window()
    if not hwnd:
        return

    # Get monitor work area dimensions
    monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd))
    work_area = monitor_info["Work"]
    monitor_x, monitor_y, monitor_width, monitor_height = (
        work_area[0],
        work_area[1],
        work_area[2] - work_area[0],
        work_area[3] - work_area[1],
    )

    # Get the window border size
    window_rect = win32gui.GetWindowRect(hwnd)
    frame_rect = win32gui.GetClientRect(hwnd)
    border_width = (window_rect[2] - window_rect[0]) - (frame_rect[2] - frame_rect[0])
    border_height = (window_rect[3] - window_rect[1]) - (frame_rect[3] - frame_rect[1])

    # Adjust the monitor dimensions to account for borders
    adjusted_width = monitor_width + border_width
    adjusted_height = monitor_height + border_height

    # Snap the window based on the direction
    if direction == "left":
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            monitor_x,
            monitor_y,
            adjusted_width // 2,
            adjusted_height,
            win32con.SWP_SHOWWINDOW,
        )
    elif direction == "right":
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            monitor_x + (monitor_width // 2) - border_width,
            monitor_y,
            adjusted_width // 2,
            adjusted_height,
            win32con.SWP_SHOWWINDOW,
        )
    elif direction == "top":
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            monitor_x,
            monitor_y,
            adjusted_width,
            adjusted_height // 2,
            win32con.SWP_SHOWWINDOW,
        )
    elif direction == "bottom":
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            monitor_x,
            monitor_y + (monitor_height // 2) - border_height,
            adjusted_width,
            adjusted_height // 2,
            win32con.SWP_SHOWWINDOW,
        )
    log_action(f"Snapped window to the {direction}.")


import ctypes


def is_zoomed(hwnd):
    """Check if a window is maximized using ctypes."""
    return ctypes.windll.user32.IsZoomed(hwnd)


def is_iconic(hwnd):
    """Check if a window is minimized using ctypes."""
    return ctypes.windll.user32.IsIconic(hwnd)


# Adjust the size of the active window
def adjust_window_size(delta):
    hwnd = get_active_window()
    if not hwnd:
        return

    # Check if the window is minimized or maximized
    if is_iconic(hwnd) or is_zoomed(hwnd):
        log_action("Cannot resize minimized or maximized window.")
        return

    # Get the current window dimensions and monitor work area
    rect = win32gui.GetWindowRect(hwnd)
    x, y, width, height = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]

    monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd))
    work_area = monitor_info["Work"]
    monitor_x, monitor_y, monitor_width, monitor_height = (
        work_area[0],
        work_area[1],
        work_area[2] - work_area[0],
        work_area[3] - work_area[1],
    )

    # Calculate screen quadrants
    mid_x = monitor_x + monitor_width // 2
    mid_y = monitor_y + monitor_height // 2

    # Calculate window's overlap with each quadrant
    overlap_top_left = max(0, min(x + width, mid_x) - max(x, monitor_x)) * max(
        0, min(y + height, mid_y) - max(y, monitor_y)
    )
    overlap_top_right = max(
        0, min(x + width, monitor_x + monitor_width) - max(x, mid_x)
    ) * max(0, min(y + height, mid_y) - max(y, monitor_y))
    overlap_bottom_left = max(0, min(x + width, mid_x) - max(x, monitor_x)) * max(
        0, min(y + height, monitor_y + monitor_height) - max(y, mid_y)
    )
    overlap_bottom_right = max(
        0, min(x + width, monitor_x + monitor_width) - max(x, mid_x)
    ) * max(0, min(y + height, monitor_y + monitor_height) - max(y, mid_y))

    # Determine the dominant quadrant
    quadrants = {
        "top_left": overlap_top_left,
        "top_right": overlap_top_right,
        "bottom_left": overlap_bottom_left,
        "bottom_right": overlap_bottom_right,
    }
    dominant_quadrant = max(quadrants, key=quadrants.get)

    # Adjust dimensions based on the dominant quadrant
    if dominant_quadrant == "top_left" or dominant_quadrant == "top_right":
        # Grow bottom side, keep width constant
        new_height = max(100, height + delta)
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOP, x, y, width, new_height, win32con.SWP_SHOWWINDOW
        )
        log_action(f"Grew bottom side by {delta} pixels.")

    elif dominant_quadrant == "bottom_left" or dominant_quadrant == "bottom_right":
        # Grow top side, keep width constant
        new_height = max(100, height + delta)
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            x,
            y - delta,
            width,
            new_height,
            win32con.SWP_SHOWWINDOW,
        )
        log_action(f"Grew top side by {delta} pixels.")

    elif dominant_quadrant == "top_left" or dominant_quadrant == "bottom_left":
        # Grow right side, keep height constant
        new_width = max(100, width + delta)
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOP, x, y, new_width, height, win32con.SWP_SHOWWINDOW
        )
        log_action(f"Grew right side by {delta} pixels.")

    elif dominant_quadrant == "top_right" or dominant_quadrant == "bottom_right":
        # Grow left side, keep height constant
        new_width = max(100, width + delta)
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            x - delta,
            y,
            new_width,
            height,
            win32con.SWP_SHOWWINDOW,
        )
        log_action(f"Grew left side by {delta} pixels.")

    else:
        log_action("No dominant quadrant detected. No resizing performed.")


# Move the active window to the next monitor
def move_to_next_monitor():
    hwnd = get_active_window()
    if not hwnd:
        return

    monitors = []

    def callback(hmonitor, hdc, lprect, data):
        monitor_info = win32api.GetMonitorInfo(hmonitor)
        monitors.append(monitor_info)

    ctypes.windll.user32.EnumDisplayMonitors(
        0,
        0,
        ctypes.WINFUNCTYPE(
            None,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_long),
            ctypes.c_ulong,
        )(callback),
        0,
    )

    if not monitors:
        return

    current_monitor = win32api.MonitorFromWindow(
        hwnd, win32con.MONITOR_DEFAULTTONEAREST
    )  # Updated
    current_index = next(
        (i for i, m in enumerate(monitors) if m["Monitor"] == current_monitor), 0
    )
    next_index = (current_index + 1) % len(monitors)

    monitor_info = monitors[next_index]
    work_area = monitor_info["Work"]
    x, y, width, height = (
        work_area[0],
        work_area[1],
        work_area[2] - work_area[0],
        work_area[3] - work_area[1],
    )
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOP, x, y, width, height, win32con.SWP_SHOWWINDOW
    )


# Register global keyboard shortcuts
def register_shortcuts():
    # Snap window shortcuts
    keyboard.add_hotkey("win+alt+left", lambda: snap_window("left"), suppress=True)
    keyboard.add_hotkey("win+alt+right", lambda: snap_window("right"), suppress=True)
    keyboard.add_hotkey("win+alt+up", lambda: snap_window("top"), suppress=True)
    keyboard.add_hotkey("win+alt+down", lambda: snap_window("bottom"), suppress=True)

    # Resize window shortcuts
    keyboard.add_hotkey("win+alt+=", lambda: adjust_window_size(50), suppress=True)
    keyboard.add_hotkey("win+alt+-", lambda: adjust_window_size(-50), suppress=True)

    # Move window shortcuts
    keyboard.add_hotkey("win+alt+ctrl+left", move_to_next_monitor, suppress=True)

    log_action("Registered all keyboard shortcuts.")


# Main function to start the app
def main():
    global running
    print(
        "Windows Management App is running... Use the tray icon to quit or press CTRL+C in the shell."
    )

    # Set up tray icon
    menu = Menu(MenuItem("Quit", quit_app))
    icon = Icon(
        "Windows Manager", create_image(), menu=menu, title="Rectangle for Windows"
    )

    # Start the tray icon in a separate thread
    import threading

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    # Register shortcuts
    register_shortcuts()

    # Main event loop
    try:
        while running:
            pass  # Keep running until `running` is set to False
    except KeyboardInterrupt:
        log_action("Exiting app via CTRL+C.")
    finally:
        keyboard.unhook_all_hotkeys()  # Clean up keyboard hooks
        print("Application stopped.")
        sys.exit()


if __name__ == "__main__":
    main()
