"""
Utility functions for embedding processing, including base64 conversion and image handling.
"""

import base64
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


def encode_local_file_to_base64(file_path: Union[str, Path]) -> str:
    try:
        # Convert to Path object for better path handling
        path = Path(file_path) if isinstance(file_path, str) else file_path

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if it's a file (not a directory)
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Read file content and encode to base64
        with open(path, "rb") as file:
            buffer = io.BytesIO(file.read())
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error converting file to base64: {str(e)}")


def encode_pil_image_to_base64(image: "Image") -> str:
    try:
        buffer = io.BytesIO()
        image.save(buffer)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error converting PIL Image to base64: {str(e)}")
