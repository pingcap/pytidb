"""
Utility functions for embedding processing, including base64 conversion and image handling.
"""

import base64
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import ParseResult, urlparse


def parse_url_if_valid(url_text: str) -> tuple[bool, Optional[ParseResult]]:
    """
    Parse a URL string and validate its format.

    Args:
        url_text: URL string to parse (should be a proper URL with scheme)

    Returns:
        Tuple of (is_valid, parsed_url) where is_valid is a boolean
        and parsed_url is the ParseResult object or None

    Note:
        This function expects properly formatted URLs with schemes (e.g., 'http://', 'https://', 'file://').
        For local file paths, use convert_local_file_to_base64() or convert_local_image_to_data_url() instead.
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


def convert_local_file_to_base64(file_path: str) -> str:
    """
    Convert a local file to base64 encoded string.

    Args:
        file_path: Path to the local file (can be absolute or relative)

    Returns:
        Base64 encoded string of the file content

    Raises:
        FileNotFoundError: If the file does not exist
        PermissionError: If the file cannot be read
        ValueError: If the file path is invalid
    """
    try:
        # Convert to Path object for better path handling
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check if it's a file (not a directory)
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Read file content and encode to base64
        with open(path, "rb") as file:
            file_content = file.read()
            base64_encoded = base64.b64encode(file_content).decode("utf-8")
            return base64_encoded

    except Exception as e:
        raise ValueError(f"Error converting file to base64: {str(e)}")


def get_image_mime_type(file_path: str) -> str:
    """
    Get the MIME type of an image file.

    Args:
        file_path: Path to the image file

    Returns:
        MIME type string (e.g., 'image/jpeg', 'image/png')
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("image/"):
        return mime_type

    # Fallback to common image formats based on file extension
    ext = Path(file_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    return mime_map.get(ext, "image/jpeg")  # Default to jpeg


def encode_image_to_base64(file_path: str) -> str:
    """
    Convert a local image file to a data URL with proper MIME type.

    Args:
        file_path: Path to the local image file

    Returns:
        Data URL string in format: data:image/type;base64,encoded_content
    """
    base64_content = convert_local_file_to_base64(file_path)
    mime_type = get_image_mime_type(file_path)
    return f"data:{mime_type};base64,{base64_content}"
