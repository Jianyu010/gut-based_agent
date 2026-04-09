"""screen.py — The Eyes: screenshot capture and image encoding."""

import base64
import hashlib
import io
from PIL import Image
import mss


def capture_screen() -> Image.Image:
    """Capture the full screen and return a PIL Image."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    return img


def image_to_base64(image: Image.Image, max_width: int = 1280,
                    fmt: str = "JPEG") -> tuple[str, float, float]:
    """Resize image to max_width and return (base64 string, scale_x, scale_y).

    scale_x / scale_y convert Claude's image coordinates to real screen coordinates.
    fmt: "JPEG" (default, fast, small) or "PNG" (lossless).
    """
    orig_w, orig_h = image.width, image.height

    if image.width > max_width:
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        image = image.resize(new_size, Image.LANCZOS)

    scale_x = orig_w / image.width
    scale_y = orig_h / image.height

    buffer = io.BytesIO()
    if fmt == "JPEG":
        image.save(buffer, format="JPEG", quality=85)
        media_type = "image/jpeg"
    else:
        image.save(buffer, format="PNG")
        media_type = "image/png"

    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64, scale_x, scale_y


def encode_pil(image: Image.Image, fmt: str = "JPEG") -> str:
    """Encode an already-resized PIL image to base64 (no scaling applied)."""
    buffer = io.BytesIO()
    if fmt == "JPEG":
        image.save(buffer, format="JPEG", quality=85)
    else:
        image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def image_hash(image: Image.Image) -> str:
    """Return a perceptual hash of the screen for change detection.
    Downsample to 64x64 grayscale and MD5 the bytes.
    """
    small = image.resize((64, 64)).convert("L")
    return hashlib.md5(small.tobytes()).hexdigest()
