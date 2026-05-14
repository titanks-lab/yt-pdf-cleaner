"""YT-PDFCleaner Core Package.

Core engine for detecting and removing tracking watermarks from SGCC PDF documents,
and converting PDF to clean Markdown.
"""

from .engine import (
    detect_watermark,
    remove_watermark,
    convert_to_markdown,
    detect_by_pattern,
)
from .scanner import scan_directory, batch_process

__all__ = [
    "detect_watermark",
    "remove_watermark",
    "convert_to_markdown",
    "scan_directory",
    "batch_process",
    "detect_by_pattern",
]
