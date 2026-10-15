import os
from typing import Tuple, Optional

# Magic byte signatures for supported file formats
FILE_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "tiff_le": [b"II*\x00"],  # Little-endian TIFF
    "tiff_be": [b"MM\x00*"],  # Big-endian TIFF
    "zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
}

MIME_MAPPINGS = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "tiff_le": "image/tiff",
    "tiff_be": "image/tiff",
    "zip": "application/zip",
}

def detect_file_type_from_bytes(header: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Cross-platform file signature detection using magic bytes.
    Does not require external C libraries like libmagic.
    Returns (format_name, mime_type) or (None, None).
    """
    if len(header) < 4:
        return None, None

    for fmt, sigs in FILE_SIGNATURES.items():
        for sig in sigs:
            if header.startswith(sig):
                fmt_clean = "tiff" if fmt in ("tiff_le", "tiff_be") else fmt
                return fmt_clean, MIME_MAPPINGS[fmt]

    return None, None

def detect_file_type(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Reads the first 32 bytes of the file and determines its genuine file type.
    """
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        return None, None

    try:
        with open(file_path, "rb") as f:
            header = f.read(32)
        return detect_file_type_from_bytes(header)
    except Exception:
        return None, None

def validate_file_signature(file_path: str, expected_extension: Optional[str] = None) -> bool:
    """
    Validates that a file's content matches its extension or is a supported claim format.
    Prevents extension spoofing (e.g. malware.exe renamed to claim.pdf).
    """
    detected_type, _ = detect_file_type(file_path)
    if not detected_type:
        return False

    if expected_extension:
        ext = expected_extension.lower().lstrip(".")
        if ext in ("jpg", "jpeg") and detected_type == "jpeg":
            return True
        if ext in ("tif", "tiff") and detected_type == "tiff":
            return True
        if ext == detected_type:
            return True
        return False

    return detected_type in ("pdf", "png", "jpeg", "tiff", "zip")
