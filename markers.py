"""markers.py — Set-of-Marks: AX element enumeration + screenshot annotation.

Queries the macOS Accessibility API for interactive elements in the frontmost app,
draws numbered red markers on the screenshot, and returns an element map so the
agent can click by marker number instead of estimating pixel coordinates.
"""

import ctypes
import ctypes.util
import time
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Load frameworks
# ---------------------------------------------------------------------------
_ax = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
_cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))

# ---------------------------------------------------------------------------
# Set up all function signatures ONCE at module level (avoids truncation bugs)
# ---------------------------------------------------------------------------
_VOIDP = ctypes.c_void_p
_INT   = ctypes.c_int
_LONG  = ctypes.c_long
_BOOL  = ctypes.c_bool
_UINT  = ctypes.c_uint32
_PID   = ctypes.c_int32

# CFStringCreateWithCString(allocator, cStr, encoding) -> CFStringRef
_cf.CFStringCreateWithCString.restype  = _VOIDP
_cf.CFStringCreateWithCString.argtypes = [_VOIDP, ctypes.c_char_p, _UINT]

# CFStringGetCString(str, buf, bufSize, encoding) -> bool
_cf.CFStringGetCString.restype  = _BOOL
_cf.CFStringGetCString.argtypes = [_VOIDP, ctypes.c_char_p, _LONG, _UINT]

# CFRelease(obj)
_cf.CFRelease.restype  = None
_cf.CFRelease.argtypes = [_VOIDP]

# CFRetain(obj) -> obj
_cf.CFRetain.restype  = _VOIDP
_cf.CFRetain.argtypes = [_VOIDP]

# CFGetTypeID(obj) -> CFTypeID (unsigned long)
_cf.CFGetTypeID.restype  = ctypes.c_ulong
_cf.CFGetTypeID.argtypes = [_VOIDP]

# CFStringGetTypeID() -> CFTypeID
_cf.CFStringGetTypeID.restype  = ctypes.c_ulong
_cf.CFStringGetTypeID.argtypes = []

# CFArrayGetCount(array) -> CFIndex
_cf.CFArrayGetCount.restype  = _LONG
_cf.CFArrayGetCount.argtypes = [_VOIDP]

# CFArrayGetValueAtIndex(array, idx) -> void*
_cf.CFArrayGetValueAtIndex.restype  = _VOIDP
_cf.CFArrayGetValueAtIndex.argtypes = [_VOIDP, _LONG]

# AXUIElementCreateApplication(pid) -> AXUIElementRef
_ax.AXUIElementCreateApplication.restype  = _VOIDP
_ax.AXUIElementCreateApplication.argtypes = [_PID]

# AXUIElementCopyAttributeValue(element, attribute, value) -> AXError
_ax.AXUIElementCopyAttributeValue.restype  = _INT
_ax.AXUIElementCopyAttributeValue.argtypes = [_VOIDP, _VOIDP, ctypes.POINTER(_VOIDP)]

# AXValueGetValue(value, type, valuePtr) -> bool
_ax.AXValueGetValue.restype  = _BOOL
_ax.AXValueGetValue.argtypes = [_VOIDP, _UINT, _VOIDP]

_UTF8 = 0x08000100  # kCFStringEncodingUTF8
_kAXErrorSuccess    = 0
_kAXValueCGPoint    = 1
_kAXValueCGSize     = 2

# ---------------------------------------------------------------------------
# Structs
# ---------------------------------------------------------------------------
class _CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

class _CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

# ---------------------------------------------------------------------------
# AX roles we annotate
# ---------------------------------------------------------------------------
INTERACTIVE_ROLES = {
    "AXButton", "AXTextField", "AXTextArea", "AXCheckBox", "AXRadioButton",
    "AXComboBox", "AXPopUpButton", "AXLink", "AXMenuItem", "AXCell",
    "AXSlider", "AXTab", "AXMenuButton", "AXDockItem",
}

MAX_MARKERS = 80
MAX_DEPTH   = 8
_TIMEOUT_S  = 0.3

# ---------------------------------------------------------------------------
# Low-level helpers (integers only, no c_void_p instances)
# ---------------------------------------------------------------------------

def _mk_cfstr(s: str) -> int:
    """Create a CFString; returns integer pointer. Caller must CFRelease."""
    return _cf.CFStringCreateWithCString(None, s.encode("utf-8"), _UTF8)


def _cfstr_to_py(ref: int) -> str:
    """Convert CFStringRef (int) to Python str. Returns '' if ref is not a CFString."""
    if not ref:
        return ""
    # Guard: only call CFStringGetCString on actual CFString objects
    if _cf.CFGetTypeID(ref) != _cf.CFStringGetTypeID():
        return ""
    buf = ctypes.create_string_buffer(512)
    ok = _cf.CFStringGetCString(ref, buf, 512, _UTF8)
    return buf.value.decode("utf-8", errors="replace") if ok else ""


def _ax_get_str_attr(elem: int, attr: str) -> str:
    """Return a string AX attribute of elem, or ''."""
    key = _mk_cfstr(attr)
    out = _VOIDP(0)
    err = _ax.AXUIElementCopyAttributeValue(elem, key, ctypes.byref(out))
    _cf.CFRelease(key)
    if err != _kAXErrorSuccess or not out.value:
        return ""
    val = _cfstr_to_py(out.value)
    _cf.CFRelease(out.value)
    return val


def _ax_get_array_attr(elem: int, attr: str) -> list[int]:
    """Return a list of retained child element pointers (ints).
    Caller must CFRelease each returned pointer when done.
    """
    key = _mk_cfstr(attr)
    out = _VOIDP(0)
    err = _ax.AXUIElementCopyAttributeValue(elem, key, ctypes.byref(out))
    _cf.CFRelease(key)
    if err != _kAXErrorSuccess or not out.value:
        return []
    arr = out.value
    count = _cf.CFArrayGetCount(arr)
    # Retain each child before releasing the array so pointers stay valid
    children = []
    for i in range(count):
        c = _cf.CFArrayGetValueAtIndex(arr, i)
        if c:
            _cf.CFRetain(c)
            children.append(c)
    _cf.CFRelease(arr)
    return children


def _ax_get_bounds(elem: int):
    """Return (x, y, w, h) screen coords or None."""
    for pos_attr, size_attr in [("AXPosition", "AXSize")]:
        key_pos  = _mk_cfstr(pos_attr)
        key_size = _mk_cfstr(size_attr)
        pos_out  = _VOIDP(0)
        size_out = _VOIDP(0)
        e1 = _ax.AXUIElementCopyAttributeValue(elem, key_pos,  ctypes.byref(pos_out))
        e2 = _ax.AXUIElementCopyAttributeValue(elem, key_size, ctypes.byref(size_out))
        _cf.CFRelease(key_pos)
        _cf.CFRelease(key_size)

        if e1 == _kAXErrorSuccess and e2 == _kAXErrorSuccess and pos_out.value and size_out.value:
            pt = _CGPoint()
            sz = _CGSize()
            ok1 = _ax.AXValueGetValue(pos_out.value,  _kAXValueCGPoint, ctypes.byref(pt))
            ok2 = _ax.AXValueGetValue(size_out.value, _kAXValueCGSize,  ctypes.byref(sz))
            _cf.CFRelease(pos_out.value)
            _cf.CFRelease(size_out.value)
            if ok1 and ok2 and sz.width > 0 and sz.height > 0:
                return (pt.x, pt.y, sz.width, sz.height)
        else:
            if pos_out.value:  _cf.CFRelease(pos_out.value)
            if size_out.value: _cf.CFRelease(size_out.value)
    return None


def _ax_get_label(elem: int) -> str:
    for attr in ("AXTitle", "AXDescription", "AXValue", "AXHelp"):
        val = _ax_get_str_attr(elem, attr)
        if val.strip():
            return val.strip()[:60]
    return ""


# ---------------------------------------------------------------------------
# Tree walk
# ---------------------------------------------------------------------------

def _walk(elem: int, screen_w: int, screen_h: int,
          results: list, deadline: float, depth: int):
    if time.time() > deadline or len(results) >= MAX_MARKERS or depth > MAX_DEPTH:
        return

    role = _ax_get_str_attr(elem, "AXRole")
    if role in INTERACTIVE_ROLES:
        bounds = _ax_get_bounds(elem)
        if bounds:
            x, y, w, h = bounds
            cx, cy = x + w / 2, y + h / 2
            # Center must be within screen bounds
            if 0 <= cx <= screen_w and 0 <= cy <= screen_h:
                results.append({
                    "role":         role,
                    "label":        _ax_get_label(elem),
                    "screen_rect":  bounds,
                    "center_screen": (cx, cy),
                })

    if len(results) < MAX_MARKERS and depth < MAX_DEPTH:
        children = _ax_get_array_attr(elem, "AXChildren")
        for child in children:
            _walk(child, screen_w, screen_h, results, deadline, depth + 1)
            _cf.CFRelease(child)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _get_pid_by_bundle(bundle_id: str) -> int | None:
    """Return PID of a running app by bundle identifier."""
    try:
        from AppKit import NSWorkspace
        for a in NSWorkspace.sharedWorkspace().runningApplications():
            if a.bundleIdentifier() == bundle_id:
                return a.processIdentifier()
    except Exception:
        pass
    return None


def get_interactive_elements(scale_x: float, scale_y: float,
                              screen_w: int = 1728, screen_h: int = 1117
                              ) -> tuple[dict, bool]:
    """Query AX trees of frontmost app + Dock. Returns (element_map, ax_available).

    element_map: {int → {"role", "label", "center_screen": (x,y), "rect_img": (x1,y1,x2,y2)}}
    """
    try:
        from AppKit import NSWorkspace

        raw: list[dict] = []
        deadline = time.time() + _TIMEOUT_S

        # --- Frontmost app ---
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app:
            pid = app.processIdentifier()
            app_elem = _ax.AXUIElementCreateApplication(pid)
            if app_elem:
                _walk(app_elem, screen_w, screen_h, raw, deadline, depth=0)
                _cf.CFRelease(app_elem)

        # --- Dock (always visible, needed to launch apps) ---
        dock_pid = _get_pid_by_bundle("com.apple.dock")
        if dock_pid and len(raw) < MAX_MARKERS:
            dock_elem = _ax.AXUIElementCreateApplication(dock_pid)
            if dock_elem:
                _walk(dock_elem, screen_w, screen_h, raw,
                      time.time() + 0.15, depth=0)
                _cf.CFRelease(dock_elem)

        if not raw:
            return {}, False

        element_map: dict = {}
        for i, e in enumerate(raw[:MAX_MARKERS], start=1):
            x, y, w, h = e["screen_rect"]
            element_map[i] = {
                "role":          e["role"],
                "label":         e["label"],
                "center_screen": e["center_screen"],
                "rect_img": (x / scale_x, y / scale_y,
                             (x + w) / scale_x, (y + h) / scale_y),
            }
        return element_map, True

    except Exception as ex:
        print(f"  [markers] AX error: {ex}")
        return {}, False


def annotate_screenshot(image: Image.Image, element_map: dict) -> Image.Image:
    """Draw numbered red boxes on a copy of the screenshot."""
    out = image.copy()
    draw = ImageDraw.Draw(out)

    font = None
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)
    except Exception:
        font = ImageFont.load_default()

    for mid, e in element_map.items():
        x1, y1, x2, y2 = (int(v) for v in e["rect_img"])
        draw.rectangle([x1, y1, x2, y2], outline=(255, 40, 40), width=2)

        lw, lh = 18, 14
        lx = max(0, x1)
        ly = max(0, y1 - lh)
        draw.rectangle([lx, ly, lx + lw, ly + lh], fill=(255, 40, 40))
        draw.text((lx + 2, ly + 1), str(mid), fill=(255, 255, 255), font=font)

    return out
