"""Scanner module for batch PDF processing.

Provides functions for:
- scan_directory: Recursively scan a directory for PDF files with watermark detection
- batch_process: Process multiple PDF files (watermark removal or Markdown conversion)
"""

import os
import sys
from typing import Any, Dict, List, Optional

from .engine import convert_to_markdown, detect_watermark, remove_watermark


def scan_directory(dir_path: str) -> List[Dict[str, Any]]:
    """Recursively scan a directory for PDF files and detect watermarks.

    Scans all ``.pdf`` files (case-insensitive) in the given directory tree.
    For each file, calls ``detect_watermark`` and collects results.

    Args:
        dir_path: Path to the directory to scan.

    Returns:
        A list of dicts, one per PDF file found, each containing:
            - path: Absolute path to the PDF file
            - name: File name only
            - size: File size in bytes
            - has_watermark: Boolean indicating watermark presence
            - streams: Number of content streams checked
            - pages: Number of pages
            - error: Error message (only present on failure)

    Example:
        >>> results = scan_directory("/path/to/pdfs")
        >>> for r in results:
        ...     status = "⚠️" if r["has_watermark"] else "✓"
        ...     print(f"{status} {r['name']} ({r['pages']} pages)")
    """
    results: List[Dict[str, Any]] = []

    if not os.path.exists(dir_path):
        return [
            {
                "path": dir_path,
                "name": os.path.basename(dir_path),
                "size": 0,
                "has_watermark": False,
                "streams": 0,
                "pages": 0,
                "error": f"Directory not found: {dir_path}",
            }
        ]

    for root, _dirs, files in os.walk(dir_path):
        for filename in sorted(files):
            if not filename.lower().endswith(".pdf"):
                continue

            filepath = os.path.join(root, filename)
            file_size = os.path.getsize(filepath)

            has_wm, info = detect_watermark(filepath)

            entry: Dict[str, Any] = {
                "path": os.path.abspath(filepath),
                "name": filename,
                "size": file_size,
                "has_watermark": has_wm,
                "streams": info.get("stream_count", 0),
                "pages": info.get("page_count", 0),
            }

            if "error" in info:
                entry["error"] = info["error"]

            results.append(entry)

    return results


def batch_process(
    files: List[str], output_dir: str, mode: str = "pdf"
) -> List[Dict[str, Any]]:
    """Process multiple PDF files in batch mode.

    For each file in the input list:
    - ``mode="pdf"``: Remove watermark and save as ``{original_name}_去水印.pdf``
    - ``mode="markdown"``: Convert to Markdown and save as ``{original_name}.md``

    Progress is printed to stdout showing which file is being processed
    (e.g., ``[3/10] Processing: document.pdf``).

    Args:
        files: List of paths to PDF files to process.
        output_dir: Directory where output files will be saved.
        mode: Processing mode — ``"pdf"`` (watermark removal) or
              ``"markdown"`` (text conversion). Default ``"pdf"``.

    Returns:
        A list of result dicts, one per input file. The dict structure
        depends on the processing mode (see ``remove_watermark`` or
        ``convert_to_markdown`` for details).

    Example:
        >>> results = batch_process(["a.pdf", "b.pdf"], "/tmp/output", mode="pdf")
        >>> print(f"Processed {len(results)} files")
    """
    total = len(files)

    if total == 0:
        return []

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    results: List[Dict[str, Any]] = []

    for idx, filepath in enumerate(files, start=1):
        print(f"[{idx}/{total}] Processing: {os.path.basename(filepath)}", flush=True)

        base_name = os.path.splitext(os.path.basename(filepath))[0]

        if mode == "pdf":
            # Watermark removal mode
            output_path = os.path.join(output_dir, f"{base_name}_去水印.pdf")
            result = remove_watermark(filepath, output_path)
            result["_source"] = filepath
            result["_output"] = output_path
            results.append(result)

        elif mode == "markdown":
            # Markdown conversion mode
            output_path = os.path.join(output_dir, f"{base_name}.md")
            result = convert_to_markdown(filepath, output_path)
            result["_source"] = filepath
            result["_output"] = output_path
            results.append(result)

        else:
            results.append(
                {
                    "success": False,
                    "error": f"Unknown mode: {mode}. Use 'pdf' or 'markdown'.",
                    "_source": filepath,
                }
            )

    return results


# --- Demo / Quick Test ---
if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python scanner.py <directory_or_file> [mode] [output_dir]")
        print("  mode: 'scan' (default), 'batch-pdf', 'batch-md'")
        sys.exit(1)

    target = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "scan"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "/tmp"

    print("=" * 60)
    print("YT-PDFCleaner — Scanner Demo")
    print("=" * 60)

    if mode == "scan" or (mode not in ("batch-pdf", "batch-md") and os.path.isdir(target)):
        # Scan mode
        print(f"\nScanning directory: {target}")
        results = scan_directory(target)
        print(f"\nFound {len(results)} PDF file(s):")
        print("-" * 60)
        for r in results:
            wm = "⚠️ WATERMARK" if r.get("has_watermark") else "✓ clean"
            err = f" [ERROR: {r.get('error', '')}]" if r.get("error") else ""
            print(f"  {wm} | {r['name']} ({r['pages']} pages, {r['size']:,} bytes){err}")

    elif mode == "batch-pdf":
        # Batch watermark removal
        files = [target] if os.path.isfile(target) else [
            os.path.join(target, f) for f in os.listdir(target)
            if f.lower().endswith(".pdf")
        ]
        print(f"\nBatch watermark removal: {len(files)} file(s) → {output_dir}")
        results = batch_process(files, output_dir, mode="pdf")
        print(f"\nResults ({len(results)} file(s)):")
        for r in results:
            status = "✅" if r.get("success") else "❌"
            name = os.path.basename(r.get("_source", "?"))
            err = f" - {r.get('error', '')}" if r.get("error") else ""
            print(f"  {status} {name}{err}")

    elif mode == "batch-md":
        # Batch Markdown conversion
        files = [target] if os.path.isfile(target) else [
            os.path.join(target, f) for f in os.listdir(target)
            if f.lower().endswith(".pdf")
        ]
        print(f"\nBatch Markdown conversion: {len(files)} file(s) → {output_dir}")
        results = batch_process(files, output_dir, mode="markdown")
        print(f"\nResults ({len(results)} file(s)):")
        for r in results:
            status = "✅" if r.get("success") else "❌"
            name = os.path.basename(r.get("_source", "?"))
            err = f" - {r.get('error', '')}" if r.get("error") else ""
            print(f"  {status} {name}{err}")

    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

    print("\n✅ Demo completed!")
