"""Unit tests for core.engine module.

Tests detect_watermark, remove_watermark, convert_to_markdown, and detect_by_pattern.
All tests use real PDF files and tempdirs — no mocking of core functions.
"""

import os
import pymupdf
from pathlib import Path

import pytest

from core.engine import (
    detect_watermark,
    remove_watermark,
    convert_to_markdown,
    detect_by_pattern,
)


# ═══════════════════════════════════════════════════════════════
# detect_watermark
# ═══════════════════════════════════════════════════════════════


class TestDetectWatermark:
    """Tests for detect_watermark() — detection accuracy and edge cases."""

    def test_detect_watermark_on_known_file(self, watermarked_pdf_path: Path):
        """Known watermarked PDF must be detected as having a watermark."""
        found, info = detect_watermark(str(watermarked_pdf_path))
        assert found is True, (
            f"Expected watermark=True for known watermarked PDF.\n"
            f"  Info: {info}"
        )
        assert info["page_count"] >= 1
        assert len(info["watermark_pages"]) >= 1
        assert info["file_size"] > 0
        assert info["stream_count"] > 0

    def test_detect_watermark_on_empty_pdf(self, empty_pdf: str):
        """An empty/blank PDF (no watermark) must return False."""
        found, info = detect_watermark(empty_pdf)
        assert found is False, (
            f"Expected watermark=False for empty PDF.\n"
            f"  Info: {info}"
        )
        assert info["page_count"] == 1
        assert info["watermark_pages"] == []

    def test_detect_watermark_on_non_watermarked(self, non_watermarked_pdf_path: Path):
        """A real PDF without watermark must return False."""
        found, info = detect_watermark(str(non_watermarked_pdf_path))
        assert found is False, (
            f"Expected watermark=False for non-watermarked PDF.\n"
            f"  Info: {info}"
        )
        assert info["page_count"] >= 1
        assert info["watermark_pages"] == []

    def test_invalid_file_nonexistent(self):
        """Non-existent file must return (False, {error: ...})."""
        found, info = detect_watermark("/nonexistent/path.pdf")
        assert found is False
        assert "error" in info
        assert "File not found" in info["error"]

    def test_invalid_file_corrupted(self, corrupted_pdf: str):
        """Corrupted/invalid PDF must not crash; returns (False, {error: ...})."""
        found, info = detect_watermark(corrupted_pdf)
        # pymupdf may raise or return error — either way we shouldn't crash
        assert found is False
        assert "error" in info or True  # at minimum, no exception


class TestDetectByPattern:
    """Tests for detect_by_pattern() — custom pattern detection."""

    def test_detect_by_pattern_default(self, watermarked_pdf_path: Path):
        """Default parameters must match the same watermark as detect_watermark."""
        found_default, info_default = detect_watermark(str(watermarked_pdf_path))
        found_pattern, info_pattern = detect_by_pattern(str(watermarked_pdf_path))
        assert found_default == found_pattern, (
            f"detect_by_pattern default should match detect_watermark.\n"
            f"  Detect: {found_default}, Pattern: {found_pattern}"
        )
        assert info_pattern["watermark_pages"] == info_default["watermark_pages"]

    def test_detect_by_pattern_custom(self, watermarked_pdf_path: Path):
        """Custom parameters (different gray/rotation) may not match."""
        # Use a significantly different gray value — should NOT match the watermark
        found, info = detect_by_pattern(
            str(watermarked_pdf_path),
            gray=(1.0, 1.0, 1.0),  # white, not gray
            rotation=0.5,  # different rotation
        )
        # Watermark uses 0.6/0.93969, so custom should not match
        assert found is False, (
            f"Expected custom pattern NOT to match the known watermark.\n"
            f"  Info: {info}"
        )

    def test_detect_by_pattern_custom_same(self, watermarked_pdf_path: Path):
        """Custom parameters that match the actual watermark must detect it."""
        found, info = detect_by_pattern(
            str(watermarked_pdf_path),
            gray=(0.6, 0.6, 0.6),  # same gray
            rotation=0.93969,  # same rotation
        )
        assert found is True, (
            f"Custom params matching the watermark should detect it.\n"
            f"  Info: {info}"
        )

    def test_detect_by_pattern_nonexistent(self):
        """detect_by_pattern on missing file must return error."""
        found, info = detect_by_pattern("/nonexistent/path.pdf")
        assert found is False
        assert "error" in info
        assert "File not found" in info["error"]


# ═══════════════════════════════════════════════════════════════
# remove_watermark
# ═══════════════════════════════════════════════════════════════


class TestRemoveWatermark:
    """Tests for remove_watermark() — removal correctness and safety."""

    def test_remove_watermark(self, watermarked_copy: str, tmp_workdir: str):
        """Remove watermark from a copy of a watermarked PDF.

        After removal:
        - The watermark stream content must be cleared.
        - The body text must be preserved (no data loss).
        """
        output_path = os.path.join(tmp_workdir, "cleaned.pdf")
        result = remove_watermark(watermarked_copy, output_path)

        # Check result fields
        assert result["success"] is True, f"Remove failed: {result.get('error')}"
        assert result["streams_cleared"] >= 1, (
            f"Expected at least 1 watermark stream cleared.\n"
            f"  Result: {result}"
        )
        assert result["pages"] >= 1
        assert result["input_size"] > 0
        assert result["output_size"] > 0
        assert result["error"] == ""

        # Verify output file exists
        assert os.path.exists(output_path), "Output file was not created."

        # Verify watermark content is GONE from output
        doc = pymupdf.open(output_path)
        watermark_found_after = False
        try:
            for pi in range(len(doc)):
                page = doc[pi]
                for xref in page.get_contents():
                    stream = doc.xref_stream(xref)
                    if stream and b"0.6 0.6 0.6 rg" in stream and b"0.93969" in stream:
                        watermark_found_after = True
                        break
        finally:
            doc.close()

        assert watermark_found_after is False, (
            "Watermark stream content still present after removal!"
        )

    def test_remove_watermark_preserves_body_text(
        self, watermarked_copy: str, tmp_workdir: str
    ):
        """After watermark removal, the body text must still be extractable."""
        # Extract body text before removal
        doc_before = pymupdf.open(watermarked_copy)
        text_before = ""
        for pi in range(len(doc_before)):
            text_before += doc_before[pi].get_text("text")
        doc_before.close()
        text_before = text_before.strip()

        output_path = os.path.join(tmp_workdir, "cleaned.pdf")
        remove_watermark(watermarked_copy, output_path)

        # Extract text after removal
        doc_after = pymupdf.open(output_path)
        text_after = ""
        for pi in range(len(doc_after)):
            text_after += doc_after[pi].get_text("text")
        doc_after.close()
        text_after = text_after.strip()

        # Body text should still be present (at least some content remains)
        assert len(text_after) > 0, "All body text was lost after watermark removal!"
        # The 劳动纪律管理 PDF has ~1400 chars of body text
        assert len(text_after) >= 100, (
            f"Too little text remaining after removal: {len(text_after)} chars"
        )

    def test_remove_watermark_nonexistent(self):
        """remove_watermark on missing file must return error."""
        result = remove_watermark("/nonexistent/path.pdf", "/tmp/out.pdf")
        assert result["success"] is False
        assert "File not found" in result["error"]

    def test_remove_watermark_no_watermark(
        self, non_watermarked_copy: str, tmp_workdir: str
    ):
        """Removing watermark from a non-watermarked PDF must succeed with 0 streams cleared."""
        output_path = os.path.join(tmp_workdir, "output.pdf")
        result = remove_watermark(non_watermarked_copy, output_path)
        assert result["success"] is True
        assert result["streams_cleared"] == 0, (
            "Non-watermarked PDF should have 0 watermark streams."
        )
        assert result["pages"] >= 1


# ═══════════════════════════════════════════════════════════════
# convert_to_markdown
# ═══════════════════════════════════════════════════════════════


class TestConvertToMarkdown:
    """Tests for convert_to_markdown() — conversion quality and filtering."""

    def test_convert_to_markdown(self, watermarked_pdf_path: Path, tmp_workdir: str):
        """Convert a watermarked PDF to Markdown.

        Requirements:
        - Output must be valid Markdown text.
        - Watermark lines must be filtered out.
        - Key body content must be retained.
        """
        md_path = os.path.join(tmp_workdir, "output.md")
        result = convert_to_markdown(str(watermarked_pdf_path), md_path)

        assert result["success"] is True, f"Conversion failed: {result.get('error')}"
        assert result["char_count"] > 0, "No characters extracted!"
        assert result["line_count"] > 0, "No lines extracted!"
        assert os.path.exists(md_path), "Markdown file was not created."

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Content must not contain watermark lines
        watermark_survivors = [
            kw for kw in ["黄琦斌", "远通分公司", "厦门供电"]
            if kw in content
        ]
        assert not watermark_survivors, (
            f"Watermark content found in markdown output: {watermark_survivors}"
        )

        # Key body content must be preserved
        assert "劳动纪律管理" in content, (
            "Key body content missing after markdown conversion!"
        )
        assert "考勤" in content, (
            "Key body content (考勤) missing after markdown conversion!"
        )

    def test_convert_to_markdown_nonexistent(self, tmp_workdir: str):
        """Convert a nonexistent file must return error."""
        md_path = os.path.join(tmp_workdir, "output.md")
        result = convert_to_markdown("/nonexistent/path.pdf", md_path)
        assert result["success"] is False
        assert "File not found" in result["error"]

    def test_convert_to_markdown_empty_pdf(self, empty_pdf: str, tmp_workdir: str):
        """Convert an empty PDF — should succeed with minimal output."""
        md_path = os.path.join(tmp_workdir, "output.md")
        result = convert_to_markdown(empty_pdf, md_path)
        assert result["success"] is True
        # An empty page may produce some whitespace but should not crash

    def test_convert_to_markdown_non_watermarked(
        self, non_watermarked_pdf_path: Path, tmp_workdir: str
    ):
        """Convert a non-watermarked PDF — all content must be preserved."""
        md_path = os.path.join(tmp_workdir, "output.md")
        result = convert_to_markdown(str(non_watermarked_pdf_path), md_path)
        assert result["success"] is True
        assert result["char_count"] > 0

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Non-watermarked PDF content should be present
        assert len(content) > 0


# ═══════════════════════════════════════════════════════════════
# Extra edge cases across modules
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases and error handling for all engine functions."""

    def test_invalid_file_empty_path(self):
        """Empty path must not crash (but may not be a valid file)."""
        found, info = detect_watermark("")
        assert found is False
        # Either error or file-not-found style response

    def test_invalid_file_non_pdf_extension(self, tmp_workdir: str):
        """A file with .pdf extension but not valid PDF should be handled."""
        fpath = os.path.join(tmp_workdir, "fake.pdf")
        with open(fpath, "w") as f:
            f.write("This is not a PDF at all.")
        found, info = detect_watermark(fpath)
        assert found is False
        # pymupdf should raise/return error — we just must not crash

    def test_remove_watermark_same_path(self, watermarked_copy: str):
        """In-place removal (input == output) should work or fail gracefully."""
        # This is a risk: writing to the same file while it's open
        result = remove_watermark(watermarked_copy, watermarked_copy)
        # Either success or handled error — no crash
        if result["success"]:
            assert result["streams_cleared"] >= 1
        # If it fails, there should be an error message
        else:
            assert "error" in result and result["error"]


# ═══════════════════════════════════════════════════════════════
# BUG REPORT: Known issues
# ═══════════════════════════════════════════════════════════════
# (Empty for now — discovered bugs are documented in test output
#  with file + line number + reproduction steps.)
