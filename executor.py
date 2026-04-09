from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import time

class ActionError(Exception):
    pass
class ClickMarkerFailed(ActionError):
    pass
class TypeTextFailed(ActionError):
    pass
class HotkeyFailed(ActionError):
    pass

def click_marker(x, y):
    try:
        mouse = MouseController()
        mouse.position = (x, y)
        mouse.click(Button.left, 1)
    except Exception as e:
        raise ClickMarkerFailed(f"Failed to click marker: {e}")

def type_text(text):
    try:
        keyboard = KeyboardController()
        for char in text:
            keyboard.press(char)
            keyboard.release(char)
    except Exception as e:
        raise TypeTextFailed(f"Failed to type text: {e}")

def hotkey(*keys):
    try:
        keyboard = KeyboardController()
        for key in keys:
            keyboard.press(key)
        for key in reversed(keys):
            keyboard.release(key)
    except Exception as e:
        raise HotkeyFailed(f"Failed to perform hotkey: {e}")

if __name__ == '__main__':
    # Example usage
    try:
        time.sleep(2)  # Wait for user to switch to the desired application window
        click_marker(100, 150)  # Adjust coordinates as needed
        type_text('hello world')
        hotkey(Key.cmd, 's')  # Save on macOS
    except ActionError as e:
        print(e)
