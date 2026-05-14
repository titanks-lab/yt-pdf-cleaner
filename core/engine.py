"""Engine module for PDF watermark detection, removal, and Markdown conversion.

Provides the core functions for:
- detect_watermark: Detect tracking watermarks in PDF documents
- remove_watermark: Remove tracking watermark content streams
- convert_to_markdown: Extract text from PDF to clean Markdown
- detect_by_pattern: Detect watermark with configurable parameters
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pymupdf  # type: ignore

from .utils import convert_lines_to_markdown


def detect_watermark(pdf_path: str) -> Tuple[bool, Dict[str, Any]]:
    """Detect tracking watermark in a PDF document.

    The watermark is identified by two characteristics in the content stream:
    1. Gray color: ``0.6 0.6 0.6 rg``
    2. Rotation matrix: ``0.93969`` (diagonal text transformation)

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        A tuple of (has_watermark: bool, info: dict).
        The info dict contains:
            - page_count: Total number of pages
            - stream_count: Total number of content streams checked
            - file_size: File size in bytes
            - watermark_pages: List of page numbers (0-indexed) where watermark was found
            - error: Error message string (only present on failure)

    Example:
        >>> found, info = detect_watermark("document.pdf")
        >>> if found:
        ...     print(f"Watermark on pages {info['watermark_pages']}")
    """
    try:
        if not os.path.exists(pdf_path):
            return False, {"error": f"File not found: {pdf_path}"}

        file_size = os.path.getsize(pdf_path)
        doc = pymupdf.open(pdf_path)
        page_count = len(doc)
        stream_count = 0
        watermark_pages: List[int] = []

        for pi in range(page_count):
            page = doc[pi]
            content_xrefs = page.get_contents()

            for xref in content_xrefs:
                stream_data = doc.xref_stream(xref)
                stream_count += 1
                if stream_data is None:
                    continue

                # Detect watermark stream: grey color + rotation matrix
                if (
                    b"0.6 0.6 0.6 rg" in stream_data
                    and b"0.93969" in stream_data
                ):
                    if pi not in watermark_pages:
                        watermark_pages.append(pi)

        doc.close()

        has_watermark = len(watermark_pages) > 0
        info: Dict[str, Any] = {
            "page_count": page_count,
            "stream_count": stream_count,
            "file_size": file_size,
            "watermark_pages": watermark_pages,
        }
        return has_watermark, info

    except Exception as e:
        return False, {"error": str(e)}


def remove_watermark(pdf_path: str, output_path: str) -> Dict[str, Any]:
    """Remove tracking watermark from a PDF document.

    The watermark lives in its own content stream, separate from body text.
    It is identified by grey color (0.6 0.6 0.6 rg) and rotation matrix
    (0.93969) in the stream data. The stream is replaced with ``b"Q\\n"`` to
    properly balance the graphics state stack (closing the ``q`` operator
    from the previous stream).

    Args:
        pdf_path: Path to the input PDF file.
        output_path: Path where the cleaned PDF will be saved.

    Returns:
        A dict containing:
            - success: True if processing completed without errors
            - input_size: Input file size in bytes
            - output_size: Output file size in bytes (or 0 on failure)
            - streams_cleared: Number of watermark streams cleared
            - pages: Number of pages in the document
            - error: Error message string (only present on failure)

    Example:
        >>> result = remove_watermark("input.pdf", "output.pdf")
        >>> if result["success"]:
        ...     print(f"Cleared {result['streams_cleared']} watermark streams")
    """
    try:
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "input_size": 0,
                "output_size": 0,
                "streams_cleared": 0,
                "pages": 0,
                "error": f"File not found: {pdf_path}",
            }

        input_size = os.path.getsize(pdf_path)
        doc = pymupdf.open(pdf_path)
        page_count = len(doc)
        watermark_count = 0

        for pi in range(page_count):
            page = doc[pi]
            content_xrefs = page.get_contents()

            for xref in content_xrefs:
                stream_data = doc.xref_stream(xref)
                if stream_data is None:
                    continue

                # Detect watermark stream
                if (
                    b"0.6 0.6 0.6 rg" in stream_data
                    and b"0.93969" in stream_data
                ):
                    # Replace with 'Q\\n' to balance graphics state stack
                    doc.update_stream(xref, b"Q\n")
                    watermark_count += 1

        # Save with garbage collection and compression
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()

        output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return {
            "success": True,
            "input_size": input_size,
            "output_size": output_size,
            "streams_cleared": watermark_count,
            "pages": page_count,
            "error": "",
        }

    except Exception as e:
        return {
            "success": False,
            "input_size": input_size if "input_size" in dir() else 0,
            "output_size": 0,
            "streams_cleared": 0,
            "pages": 0,
            "error": str(e),
        }


def convert_to_markdown(pdf_path: str, output_path: str) -> Dict[str, Any]:
    """Convert a PDF document to clean Markdown text.

    Pipeline:
    1. Extract text from each page using PyMuPDF's text extraction
    2. Filter out watermark lines (containing SGCC tracking keywords)
    3. Repair cross-page hyphenation breaks
    4. Merge lines into paragraphs at sentence boundaries
    5. Write clean Markdown output

    Watermark keywords filtered:
    - "国网福建省", "厦门供电", "远通", "远通分公司", "黄琦斌"
    - Date patterns like "2025-04-14"

    Args:
        pdf_path: Path to the input PDF file.
        output_path: Path where the Markdown file will be saved.

    Returns:
        A dict containing:
            - success: True if processing completed without errors
            - char_count: Number of characters in the Markdown output
            - line_count: Number of lines in the Markdown output
            - output_path: Path to the saved Markdown file
            - error: Error message string (only present on failure)

    Example:
        >>> result = convert_to_markdown("input.pdf", "output.md")
        >>> print(f"Extracted {result['char_count']} chars to {result['output_path']}")
    """
    try:
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "char_count": 0,
                "line_count": 0,
                "output_path": output_path,
                "error": f"File not found: {pdf_path}",
            }

        doc = pymupdf.open(pdf_path)
        all_lines: List[str] = []

        for pi in range(len(doc)):
            page = doc[pi]
            text = page.get_text("text")
            page_lines = text.split("\n")
            all_lines.extend(page_lines)

        doc.close()

        # Convert to clean Markdown using our utility module
        markdown_text = convert_lines_to_markdown(all_lines, remove_watermark=True)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)

        char_count = len(markdown_text)
        line_count = len(markdown_text.split("\n"))

        return {
            "success": True,
            "char_count": char_count,
            "line_count": line_count,
            "output_path": os.path.abspath(output_path),
            "error": "",
        }

    except Exception as e:
        return {
            "success": False,
            "char_count": 0,
            "line_count": 0,
            "output_path": output_path,
            "error": str(e),
        }


def detect_by_pattern(
    pdf_path: str,
    gray: Tuple[float, float, float] = (0.6, 0.6, 0.6),
    rotation: float = 0.93969,
) -> Tuple[bool, Dict[str, Any]]:
    """Detect watermark with configurable pattern parameters.

    Same detection logic as ``detect_watermark``, but allows customizing the
    gray color values and rotation matrix value to detect different types of
    watermarks.

    The color is formatted as ``{r} {g} {b} rg`` in the content stream,
    and the rotation value is searched as a substring in the stream data.

    Args:
        pdf_path: Path to the PDF file to check.
        gray: Tuple of (R, G, B) values for the watermark color.
              Default (0.6, 0.6, 0.6) — standard SGCC tracking watermark.
        rotation: The rotation matrix value to search for.
                  Default 0.93969 — standard SGCC watermark rotation.

    Returns:
        A tuple of (has_watermark: bool, info: dict) with the same structure
        as ``detect_watermark``.

    Example:
        >>> # Detect a different watermark pattern
        >>> found, info = detect_by_pattern(
        ...     "doc.pdf", gray=(0.5, 0.5, 0.5), rotation=0.86603
        ... )
    """
    try:
        if not os.path.exists(pdf_path):
            return False, {"error": f"File not found: {pdf_path}"}

        file_size = os.path.getsize(pdf_path)
        doc = pymupdf.open(pdf_path)
        page_count = len(doc)
        stream_count = 0
        watermark_pages: List[int] = []

        # Build the color pattern string to search in stream
        color_str = f"{gray[0]} {gray[1]} {gray[2]} rg".encode("ascii")
        rotation_str = str(rotation).encode("ascii")

        for pi in range(page_count):
            page = doc[pi]
            content_xrefs = page.get_contents()

            for xref in content_xrefs:
                stream_data = doc.xref_stream(xref)
                stream_count += 1
                if stream_data is None:
                    continue

                if color_str in stream_data and rotation_str in stream_data:
                    if pi not in watermark_pages:
                        watermark_pages.append(pi)

        doc.close()

        has_watermark = len(watermark_pages) > 0
        info: Dict[str, Any] = {
            "page_count": page_count,
            "stream_count": stream_count,
            "file_size": file_size,
            "watermark_pages": watermark_pages,
        }
        return has_watermark, info

    except Exception as e:
        return False, {"error": str(e)}


# --- Demo / Quick Test ---
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python engine.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp"

    print("=" * 60)
    print("YT-PDFCleaner — Engine Demo")
    print("=" * 60)

    # 1. Detect watermark
    print(f"\n[1/3] Detecting watermark in: {pdf_path}")
    has_wm, info = detect_watermark(pdf_path)
    print(f"  Has watermark: {has_wm}")
    print(f"  Info: {json.dumps(info, indent=2, ensure_ascii=False)}")

    if has_wm:
        # 2. Remove watermark
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        clean_pdf = os.path.join(output_dir, f"{base_name}_去水印.pdf")
        print(f"\n[2/3] Removing watermark → {clean_pdf}")
        result = remove_watermark(pdf_path, clean_pdf)
        print(f"  Success: {result['success']}")
        print(f"  Input size: {result['input_size']:,} bytes")
        print(f"  Output size: {result['output_size']:,} bytes")
        print(f"  Streams cleared: {result['streams_cleared']}")
        if result.get("error"):
            print(f"  Error: {result['error']}")

        # 3. Convert to Markdown
        md_path = os.path.join(output_dir, f"{base_name}.md")
        print(f"\n[3/3] Converting to Markdown → {md_path}")
        md_result = convert_to_markdown(pdf_path, md_path)
        print(f"  Success: {md_result['success']}")
        print(f"  Characters: {md_result['char_count']}")
        print(f"  Lines: {md_result['line_count']}")
        if md_result.get("error"):
            print(f"  Error: {md_result['error']}")

        print("\n✅ Demo completed!")
    else:
        print("\nNo watermark detected — skipping removal and conversion.")
