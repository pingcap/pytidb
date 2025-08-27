"""
Utility functions for embedding processing, including base64 conversion and image handling.
"""

import base64
from collections.abc import Mapping
import io
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Union
from urllib.parse import ParseResult, urlparse

if TYPE_CHECKING:
    from PIL.Image import Image


def parse_url_safely(url_text: str) -> tuple[bool, Optional[ParseResult]]:
    """
    Parse a URL string and validate its format.

    Args:
        url_text: URL string to parse (should be a proper URL with scheme)

    Returns:
        Tuple of (is_valid, parsed_url) where is_valid is a boolean
        and parsed_url is the ParseResult object or None

    Note:
        This function expects properly formatted URLs with schemes (e.g., 'http://', 'https://', 'file://').
        For local file paths, use file_to_base64() or image_file_to_data_url() instead.
    """
    try:
        parsed = urlparse(url_text)
        # For file URLs, we don't require netloc
        if parsed.scheme == "file":
            is_valid = bool(parsed.scheme) and bool(parsed.path)
        else:
            is_valid = bool(parsed.scheme) and bool(parsed.netloc)
        return is_valid, parsed
    except Exception:
        return False, None


def compress_image_if_needed(
    image: "Image", max_base64_length: int = 100000
) -> "Image":
    """
    Compress an image if its base64 representation would be too large.

    Args:
        image: PIL Image object
        max_base64_length: Maximum allowed base64 string length

    Returns:
        Compressed PIL Image object
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError(
            "PIL (Pillow) is required for image processing. Install it with: pip install Pillow"
        )

    # First try with original quality
    buffer = io.BytesIO()
    image.save(buffer, format=image.format or "JPEG", quality=95)
    base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

    if len(base64_str) <= max_base64_length:
        return image

    # If too large, try reducing quality progressively
    for quality in [85, 70, 50, 30]:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        if len(base64_str) <= max_base64_length:
            # Return compressed image
            buffer.seek(0)
            return Image.open(buffer)

    # If still too large, resize the image
    original_size = image.size
    for scale in [0.8, 0.6, 0.4, 0.2]:
        new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        resized_image.save(buffer, format="JPEG", quality=70)
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        if len(base64_str) <= max_base64_length:
            buffer.seek(0)
            return Image.open(buffer)

    # If even the smallest version is too large, return the smallest version anyway
    return resized_image


def encode_local_file_to_base64(
    file_path: Union[str, Path], max_base64_length: Optional[int] = None
) -> str:
    try:
        # Convert to Path object for better path handling
        path = Path(file_path) if isinstance(file_path, str) else file_path

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if it's a file (not a directory)
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # If a max length is provided and it's an image file, compress it
        if max_base64_length is not None and path.suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
        ]:
            try:
                from PIL import Image

                image = Image.open(path)
                compressed_image = compress_image_if_needed(
                    image, max_base64_length=max_base64_length
                )
                buffer = io.BytesIO()
                compressed_image.save(buffer, format="JPEG", quality=70)
                return base64.b64encode(buffer.getvalue()).decode("utf-8")
            except ImportError:
                # Fall back to normal encoding if PIL is not available
                pass

        # Read file content and encode to base64
        with open(path, "rb") as file:
            buffer = io.BytesIO(file.read())
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error converting file to base64: {str(e)}")


def encode_pil_image_to_base64(
    image: "Image", max_base64_length: Optional[int] = None
) -> str:
    try:
        if max_base64_length is not None:
            image = compress_image_if_needed(image, max_base64_length=max_base64_length)

        buffer = io.BytesIO()
        image.save(buffer, format=image.format or "PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to encode PIL Image to base64: {str(e)}")


def deep_merge(*dicts: Optional[dict]) -> dict:
    """
    Deeply merge one or more dictionaries into the first one (in-place).
    Later dictionaries override earlier ones.
    """
    if not dicts:
        return {}

    # Filter out None values and convert to list
    valid_dicts = [d for d in dicts if d is not None]
    if not valid_dicts:
        return {}

    def _deep_merge(d: dict, u: dict) -> dict:
        for k, v in u.items():
            if k in d and isinstance(d[k], Mapping) and isinstance(v, Mapping):
                _deep_merge(d[k], v)
            else:
                d[k] = v
        return d

    result = valid_dicts[0].copy()
    for u in valid_dicts[1:]:
        _deep_merge(result, u)
    return result
