"""executor.py — The Hands: translate actions into mouse/keyboard events."""

import subprocess
import time
import pyautogui

# Emergency brake: move mouse to any corner to abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1  # small delay between pyautogui calls

_SCREEN_W, _SCREEN_H = pyautogui.size()

KEY_MAP = {
    "enter": "enter",
    "tab": "tab",
    "escape": "escape",
    "esc": "escape",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
}


def execute(action: dict, scale_x: float = 1.0, scale_y: float = 1.0,
            element_map: dict = None) -> tuple[bool, str]:
    """Dispatch action dict. Returns (success, output_text).
    output_text is non-empty only for shell actions.
    """
    act = action.get("action", "").lower()
    coords = action.get("coordinates")
    text = action.get("text")

    if act == "click_marker":
        if not element_map or text is None:
            print("  [executor] click_marker requires element_map and marker number in text")
            return False, ""
        try:
            marker_id = int(str(text))
        except ValueError:
            print(f"  [executor] click_marker: invalid marker id '{text}'")
            return False, ""
        elem = element_map.get(marker_id)
        if not elem:
            print(f"  [executor] click_marker: marker {marker_id} not in element_map")
            return False, ""
        sx, sy = elem["center_screen"]
        print(f"  [executor] click_marker #{marker_id} ({elem['label']!r}) → screen ({int(sx)}, {int(sy)})")
        return safe_click(int(sx), int(sy)), ""

    elif act == "click":
        if not coords or len(coords) < 2:
            print("  [executor] click requires coordinates")
            return False, ""
        x = int(coords[0] * scale_x)
        y = int(coords[1] * scale_y)
        return safe_click(x, y), ""

    elif act == "type":
        if text is None:
            print("  [executor] type requires text")
            return False, ""
        return safe_type(str(text)), ""

    elif act == "press":
        if text is None:
            print("  [executor] press requires text (key name)")
            return False, ""
        return safe_press(str(text).lower()), ""

    elif act == "scroll":
        direction = str(text).lower() if text else "down"
        return safe_scroll(direction), ""

    elif act == "shell":
        print("  [executor] shell action is disabled — use click_marker to interact with the UI")
        return False, ""

    elif act == "done":
        return True, ""

    else:
        print(f"  [executor] unknown action: {act}")
        return False, ""


def safe_click(x: int, y: int) -> bool:
    """Left-click at (x, y), clamping to screen bounds."""
    orig = (x, y)
    x = max(0, min(x, _SCREEN_W - 1))
    y = max(0, min(y, _SCREEN_H - 1))
    if (x, y) != orig:
        print(f"  [executor] clamped ({orig[0]}, {orig[1]}) → ({x}, {y}) to fit {_SCREEN_W}x{_SCREEN_H}")
    pyautogui.click(x, y)
    time.sleep(0.3)
    return True


def safe_type(text: str) -> bool:
    """Type text via clipboard paste (handles all characters reliably)."""
    import pyperclip
    pyperclip.copy(text)
    pyautogui.hotkey("cmd", "v")
    time.sleep(0.3)
    return True


def safe_press(key: str) -> bool:
    """Press a key or hotkey combo (e.g. 'enter', 'cmd+space', 'ctrl+c')."""
    if "+" in key:
        # Modifier combo: split and call hotkey
        parts = [p.strip() for p in key.split("+")]
        parts = [KEY_MAP.get(p, p) for p in parts]
        pyautogui.hotkey(*parts)
    else:
        mapped = KEY_MAP.get(key, key)
        pyautogui.press(mapped)
    time.sleep(0.2)
    return True


def safe_shell(cmd: str) -> tuple[bool, str]:
    """Run a shell command. Returns (success, output_text) where output_text
    is stdout (or stderr on failure) — useful for verification commands."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip()
        print(f"  [executor] shell error: {output}")
        return False, output
    output = result.stdout.strip()
    if output:
        print(f"  [executor] shell output: {output}")
    time.sleep(1.0)
    return True, output


def safe_scroll(direction: str, clicks: int = 3) -> bool:
    """Scroll up or down."""
    amount = clicks if direction == "up" else -clicks
    pyautogui.scroll(amount)
    time.sleep(0.3)
    return True
