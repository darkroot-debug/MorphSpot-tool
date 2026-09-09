"""
Image I/O and preprocessing utility functions for the forensics engine.
"""
import base64
import io
import os
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageOps


def load_image(
    source: Union[str, bytes, io.BytesIO, Image.Image],
    max_dimension: Optional[int] = 1600
) -> Tuple[np.ndarray, Image.Image, Optional[dict]]:
    """
    Loads an image from various input sources into both NumPy (RGB) and PIL formats,
    preserving raw EXIF metadata.
    
    Returns:
        rgb_array (np.ndarray): Image as RGB uint8 array (H, W, 3)
        pil_image (Image.Image): PIL Image object with metadata
        raw_exif (Optional[dict]): Extracted raw EXIF dictionary if present
    """
    pil_img: Optional[Image.Image] = None
    raw_exif: Optional[dict] = None

    if isinstance(source, str):
        # Could be file path or base64 data string
        if source.startswith("data:image") or ";base64," in source:
            base64_data = source.split(";base64,")[-1]
            image_bytes = base64.b64decode(base64_data)
            pil_img = Image.open(io.BytesIO(image_bytes))
        else:
            pil_img = Image.open(source)
    elif isinstance(source, bytes):
        pil_img = Image.open(io.BytesIO(source))
    elif isinstance(source, io.BytesIO):
        pil_img = Image.open(source)
    elif isinstance(source, Image.Image):
        pil_img = source.copy()
    else:
        raise ValueError(f"Unsupported image source type: {type(source)}")

    # Extract raw EXIF before any operations that might strip it
    try:
        raw_exif = pil_img.getexif()
    except Exception:
        raw_exif = None

    # Handle EXIF orientation if needed
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass

    # Ensure RGB format (strip alpha channel for standard forensic metrics while keeping background clean)
    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
        if pil_img.mode == "P":
            pil_img = pil_img.convert("RGBA")
        bg.paste(pil_img, mask=pil_img.split()[-1] if len(pil_img.split()) > 3 else None)
        pil_img = bg
    elif pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    # Resize if exceeds max dimension to avoid memory bloat, keeping aspect ratio
    if max_dimension and (pil_img.width > max_dimension or pil_img.height > max_dimension):
        pil_img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    rgb_array = np.array(pil_img, dtype=np.uint8)
    return rgb_array, pil_img, raw_exif


def compute_image_sha256(source: Union[str, bytes, io.BytesIO, np.ndarray]) -> str:
    """Computes cryptographic SHA-256 hash of an image for evidence integrity."""
    import hashlib
    if isinstance(source, str):
        if os.path.exists(source):
            with open(source, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        elif source.startswith("data:image"):
            b64_data = source.split(";base64,")[-1]
            return hashlib.sha256(base64.b64decode(b64_data)).hexdigest()
        else:
            return hashlib.sha256(source.encode("utf-8")).hexdigest()
    elif isinstance(source, bytes):
        return hashlib.sha256(source).hexdigest()
    elif isinstance(source, io.BytesIO):
        return hashlib.sha256(source.getvalue()).hexdigest()
    elif isinstance(source, np.ndarray):
        return hashlib.sha256(source.tobytes()).hexdigest()
    return "N/A"


def array_to_pil(img_array: np.ndarray) -> Image.Image:
    """Converts a numpy uint8 array (RGB or Grayscale) to a PIL Image."""
    if img_array.dtype != np.uint8:
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    return Image.fromarray(img_array)


def array_to_base64_png(img_array: np.ndarray) -> str:
    """Converts a numpy array to base64 encoded PNG string (data:image/png;base64,...)."""
    pil_img = array_to_pil(img_array)
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"
