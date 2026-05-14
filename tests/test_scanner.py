"""Unit tests for core.scanner module.

Tests scan_directory, batch_process with PDF/Markdown modes.
All tests use real PDF files and tempdirs.
"""

import os
import shutil
from pathlib import Path
from typing import List

import pytest

from core.scanner import scan_directory, batch_process


# ═══════════════════════════════════════════════════════════════
# scan_directory
# ═══════════════════════════════════════════════════════════════


class TestScanDirectory:
    """Tests for scan_directory() — scanning directories for watermarked PDFs."""

    def test_scan_directory(self, tmp_workdir: str, watermarked_pdf_path: Path):
        """Scan a directory containing a known watermarked PDF.

        Must find the file and correctly report has_watermark=True.
        """
        # Copy the watermarked PDF into the temp dir
        dst = os.path.join(tmp_workdir, "doc.pdf")
        shutil.copy2(str(watermarked_pdf_path), dst)

        results = scan_directory(tmp_workdir)

        assert len(results) == 1, f"Expected 1 PDF, found {len(results)}"
        r = results[0]
        assert r["has_watermark"] is True, (
            f"Watermark not detected in scanned file.\n"
            f"  Result: {r}"
        )
        assert r["name"] == "doc.pdf"
        assert r["size"] > 0
        assert r["pages"] >= 1
        assert "error" not in r or not r.get("error")

    def test_scan_directory_multiple_pdfs(
        self,
        tmp_workdir: str,
        watermarked_pdf_path: Path,
        non_watermarked_pdf_path: Path,
    ):
        """Scan a directory with both watermarked and clean PDFs."""
        shutil.copy2(str(watermarked_pdf_path), os.path.join(tmp_workdir, "wm.pdf"))
        shutil.copy2(
            str(non_watermarked_pdf_path), os.path.join(tmp_workdir, "clean.pdf")
        )

        results = scan_directory(tmp_workdir)

        assert len(results) == 2, f"Expected 2 PDFs, found {len(results)}"

        # Find each by name
        by_name = {r["name"]: r for r in results}
        assert "wm.pdf" in by_name
        assert "clean.pdf" in by_name
        assert by_name["wm.pdf"]["has_watermark"] is True
        assert by_name["clean.pdf"]["has_watermark"] is False

    def test_empty_directory(self, tmp_workdir: str):
        """An empty directory (no PDFs) must return an empty list."""
        results = scan_directory(tmp_workdir)
        assert results == [], f"Expected empty list, got {len(results)} results"

    def test_nonexistent_directory(self):
        """A nonexistent directory must return a single error entry."""
        results = scan_directory("/nonexistent/directory/path")
        assert len(results) == 1, f"Expected 1 error entry, got {len(results)}"
        r = results[0]
        assert "error" in r
        assert "Directory not found" in r["error"]
        assert r["has_watermark"] is False

    def test_scan_directory_recursive(
        self, tmp_workdir: str, watermarked_pdf_path: Path
    ):
        """Scan must recurse into subdirectories."""
        subdir = os.path.join(tmp_workdir, "sub", "nested")
        os.makedirs(subdir, exist_ok=True)
        shutil.copy2(str(watermarked_pdf_path), os.path.join(subdir, "nested.pdf"))

        results = scan_directory(tmp_workdir)

        assert len(results) == 1, f"Expected 1 PDF in subdir, found {len(results)}"
        assert results[0]["has_watermark"] is True
        assert "nested.pdf" in results[0]["path"]

    def test_scan_directory_non_pdf_ignored(self, tmp_workdir: str):
        """Non-PDF files must be ignored during scanning."""
        # Create a .txt file and a .docx file
        for name in ["readme.txt", "data.docx", "image.png"]:
            fpath = os.path.join(tmp_workdir, name)
            with open(fpath, "w") as f:
                f.write("dummy content")

        results = scan_directory(tmp_workdir)
        assert results == [], f"Expected 0 PDFs, found {len(results)}"


# ═══════════════════════════════════════════════════════════════
# batch_process
# ═══════════════════════════════════════════════════════════════


class TestBatchProcess:
    """Tests for batch_process() — batch watermark removal and Markdown conversion."""

    def test_batch_process_pdf_mode(
        self, tmp_workdir: str, watermarked_pdf_path: Path
    ):
        """Batch process in 'pdf' mode: remove watermark from a single PDF.

        Must:
        - Create a _去水印.pdf output file.
        - Report success with streams_cleared >= 1.
        """
        output_dir = os.path.join(tmp_workdir, "output")
        files = [str(watermarked_pdf_path)]

        results = batch_process(files, output_dir, mode="pdf")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        r = results[0]
        assert r["success"] is True, f"Batch PDF removal failed: {r.get('error')}"
        assert r["streams_cleared"] >= 1
        assert r["pages"] >= 1

        # Check output file exists
        output_path = r.get("_output", "")
        assert output_path and os.path.exists(output_path), (
            f"Output file not found: {output_path}"
        )
        assert "_去水印.pdf" in output_path

    def test_batch_process_markdown_mode(
        self, tmp_workdir: str, watermarked_pdf_path: Path
    ):
        """Batch process in 'markdown' mode: convert PDF to Markdown.

        Must:
        - Create a .md output file.
        - Report success with char_count > 0.
        """
        output_dir = os.path.join(tmp_workdir, "output")
        files = [str(watermarked_pdf_path)]

        results = batch_process(files, output_dir, mode="markdown")

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        r = results[0]
        assert r["success"] is True, (
            f"Batch Markdown conversion failed: {r.get('error')}"
        )
        assert r["char_count"] > 0
        assert r["line_count"] > 0

        # Check output file exists
        output_path = r.get("_output", "")
        assert output_path and os.path.exists(output_path), (
            f"Output file not found: {output_path}"
        )
        assert output_path.endswith(".md")

    def test_batch_process_multiple_files(
        self, tmp_workdir: str, watermarked_pdf_path: Path,
        non_watermarked_pdf_path: Path
    ):
        """Batch process multiple files at once."""
        output_dir = os.path.join(tmp_workdir, "output")
        files = [str(watermarked_pdf_path), str(non_watermarked_pdf_path)]

        results = batch_process(files, output_dir, mode="pdf")

        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        for r in results:
            assert r["success"] is True, f"File failed: {r.get('error')}"
            output_path = r.get("_output", "")
            assert os.path.exists(output_path)

    def test_batch_process_empty_list(self, tmp_workdir: str):
        """Batch process with empty file list must return empty list."""
        results = batch_process([], tmp_workdir, mode="pdf")
        assert results == [], f"Expected empty list, got {len(results)}"

    def test_batch_process_invalid_mode(
        self, tmp_workdir: str, watermarked_pdf_path: Path
    ):
        """Invalid mode must return error entries."""
        output_dir = os.path.join(tmp_workdir, "output")
        files = [str(watermarked_pdf_path)]

        results = batch_process(files, output_dir, mode="invalid_mode")

        assert len(results) == 1
        r = results[0]
        assert r["success"] is False
        assert "error" in r
        assert "Unknown mode" in r["error"]

    def test_batch_process_creates_output_dir(
        self, tmp_workdir: str, watermarked_pdf_path: Path
    ):
        """batch_process must create the output directory if it doesn't exist."""
        output_dir = os.path.join(tmp_workdir, "nonexistent", "deep", "output")
        files = [str(watermarked_pdf_path)]

        results = batch_process(files, output_dir, mode="pdf")

        assert len(results) == 1
        assert results[0]["success"] is True
        assert os.path.isdir(output_dir), "Output directory was not created!"


# ═══════════════════════════════════════════════════════════════
# Bug Report
# ═══════════════════════════════════════════════════════════════
# (Empty for now — discovered during test run)
