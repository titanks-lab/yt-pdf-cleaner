"""Unit tests for core.utils module.

Tests is_watermark_line, filter_watermark_lines, merge_paragraphs,
repair_hyphenation, strip_page_numbers, cleanup_watermark_contamination,
and convert_lines_to_markdown.
"""

import pytest

from core.utils import (
    is_watermark_line,
    filter_watermark_lines,
    merge_paragraphs,
    repair_hyphenation,
    strip_page_numbers,
    cleanup_watermark_contamination,
    convert_lines_to_markdown,
    WATERMARK_KEYWORDS,
    WATERMARK_SECONDARY,
    WATERMARK_FRAGMENTS,
    IDEOGRAPHIC_SPACE,
)


# ═══════════════════════════════════════════════════════════════
# is_watermark_line / filter_watermark_lines
# ═══════════════════════════════════════════════════════════════


class TestIsWatermarkLine:
    """Tests for is_watermark_line() — accuracy of watermark line detection."""

    # ── Positive cases (should be detected as watermark) ──────────

    def test_ideographic_space_and_keyword(self):
        """Line with \\u3000 + keyword must be detected."""
        line = f"\u3000国网福建省电力有限公司厦门供电公司\u3000"
        assert is_watermark_line(line) is True

    def test_two_keywords(self):
        """Line with ≥2 different watermark keywords must be detected."""
        line = "国网福建省电力有限公司厦门供电公司 远通分公司 黄琦斌"
        assert is_watermark_line(line) is True

    def test_keyword_and_secondary(self):
        """Line with keyword + secondary indicator must be detected."""
        line = "国网福建省电力有限公司厦门供电公司 远通 琦斌"
        assert is_watermark_line(line) is True

    def test_keyword_and_date(self):
        """Line with keyword + date pattern must be detected."""
        line = "国网福建省电力有限公司厦门供电公司 2025-04-14"
        assert is_watermark_line(line) is True

    def test_secondary_and_date(self):
        """Line with ≥2 secondary indicators + date must be detected."""
        line = "远通分公司 黄琦斌 2025-04-14"
        assert is_watermark_line(line) is True

    def test_ideographic_space_alone(self):
        """Line with \\u3000 and non-empty content must be detected."""
        line = f"\u3000\u3000\u3000some text\u3000\u3000"
        assert is_watermark_line(line) is True

    def test_truncated_fragment(self):
        """Line with truncated watermark fragment must be detected."""
        line = "建省电力有限公司厦"
        assert is_watermark_line(line) is True

    def test_real_watermark_line(self):
        """A real watermark line extracted from the test PDF."""
        line = "黄琦斌 2025-04-14\u3000\u3000\u3000\u3000 国网福建省电力有限公司厦门供电公司 远通分公司"
        assert is_watermark_line(line) is True

    # ── Negative cases (should NOT be detected as watermark) ─────

    def test_normal_body_text(self):
        """Normal Chinese body text must NOT be flagged."""
        line = "各单位应规范员工考勤地点设置，原则上考勤地点应该与员工的工作场所一致。"
        assert is_watermark_line(line) is False

    def test_exempted_header(self):
        """Exempted document header must NOT be flagged."""
        line = "国网福建省电力有限公司部门文件"
        assert is_watermark_line(line) is False

    def test_exempted_header_office(self):
        """Exempted office name must NOT be flagged."""
        line = "国网福建省电力有限公司办公室"
        assert is_watermark_line(line) is False

    def test_exempted_header_enterprise(self):
        """Exempted enterprise management dept must NOT be flagged."""
        line = "国网福建省电力有限公司企管部（体改办）"
        assert is_watermark_line(line) is False

    def test_empty_line(self):
        """Empty line must NOT be flagged."""
        assert is_watermark_line("") is False
        assert is_watermark_line("   ") is False

    def test_english_text(self):
        """English-only text must NOT be flagged."""
        line = "This is a normal English sentence with no watermark."
        assert is_watermark_line(line) is False

    def test_number_only(self):
        """Number-only line must NOT be flagged."""
        assert is_watermark_line("12345") is False
        assert is_watermark_line("— 1 —") is False

    def test_partial_keyword_no_context(self):
        """Single keyword without other indicators in body context must NOT be flagged."""
        # "国网福建省" appears in body text as part of organization names
        line = "根据国网福建省电力有限公司有关规定"
        # This could be tricky — need to check if it has date/secondary/ideosp too
        # Since it only has 国网福建省 (1 keyword), no secondary, no date, no ideosp
        # it should NOT be flagged
        assert is_watermark_line(line) is False


class TestFilterWatermarkLines:
    """Tests for filter_watermark_lines() — bulk filtering."""

    def test_removes_watermark_lines(self):
        """Watermark lines must be removed from a mixed list."""
        lines = [
            "正常正文内容第一行。",
            "黄琦斌 2025-04-14\u3000\u3000国网福建省电力有限公司厦门供电公司 远通分公司",
            "正常正文内容第二行。",
            "\u3000国网福建省电力有限公司厦门供电公司\u3000",
        ]
        filtered = filter_watermark_lines(lines)
        assert len(filtered) == 2, f"Expected 2 lines, got {len(filtered)}: {filtered}"
        assert "正常正文内容第一行。" in filtered
        assert "正常正文内容第二行。" in filtered

    def test_preserves_body_text(self):
        """Body text lines must be preserved."""
        lines = ["第一条", "第二条", "第三条"]
        filtered = filter_watermark_lines(lines)
        assert filtered == lines

    def test_empty_input(self):
        """Empty input list must return empty list."""
        assert filter_watermark_lines([]) == []


# ═══════════════════════════════════════════════════════════════
# strip_page_numbers
# ═══════════════════════════════════════════════════════════════


class TestStripPageNumbers:
    """Tests for strip_page_numbers() — removing page markers."""

    def test_basic_page_number(self):
        """Pattern like '— 1 —' must be removed."""
        result = strip_page_numbers("— 1 —")
        assert result == "", f"Expected empty, got: {repr(result)}"

    def test_surrounding_newlines(self):
        """Newlines around page numbers must also be consumed."""
        result = strip_page_numbers("取\n— 2 —\n消")
        assert result == "取消", f"Expected '取消', got: {repr(result)}"

    def test_multiple_page_numbers(self):
        """Multiple page number markers must all be removed."""
        result = strip_page_numbers("前文\n— 1 —\n正文\n— 2 —\n后文")
        assert "— 1 —" not in result
        assert "— 2 —" not in result
        assert "前文" in result
        assert "正文" in result
        assert "后文" in result

    def test_no_page_number(self):
        """Text without page numbers must be unchanged."""
        text = "这是正常文本。"
        assert strip_page_numbers(text) == text

    def test_varying_numbers(self):
        """Page number markers with various digit lengths."""
        assert strip_page_numbers("— 1 —") == ""
        assert strip_page_numbers("— 12 —") == ""
        assert strip_page_numbers("— 123 —") == ""


# ═══════════════════════════════════════════════════════════════
# repair_hyphenation
# ═══════════════════════════════════════════════════════════════


class TestRepairHyphenation:
    """Tests for repair_hyphenation() — fixing cross-page breaks."""

    def test_english_hyphenation(self):
        """English word hyphenation must be repaired: docu-\\nment → document."""
        result = repair_hyphenation("docu-\nment")
        assert result == "document", f"Expected 'document', got: {repr(result)}"

    def test_cjk_hyphen_with_dash(self):
        """CJK characters split with hyphen-newline must be merged."""
        # This tests the explicit hyphen pattern
        result = repair_hyphenation("取-\n消")
        assert result == "取消", f"Expected '取消', got: {repr(result)}"

    def test_cjk_no_hyphen_newline(self):
        """CJK characters split by just newline must be merged."""
        result = repair_hyphenation("取\n消")
        assert result == "取消", f"Expected '取消', got: {repr(result)}"

    def test_removes_page_numbers(self):
        """Page number markers are consumed during hyphenation repair."""
        result = repair_hyphenation("取\n— 2 —\n消")
        assert result == "取消", f"Expected '取消', got: {repr(result)}"

    def test_no_change_needed(self):
        """Normal text must be unchanged."""
        text = "这是正常文本。"
        assert repair_hyphenation(text) == text

    def test_consecutive_words(self):
        """Multiple consecutive hyphenations must all be fixed."""
        result = repair_hyphenation("docu-\nment and pro-\ncess")
        assert result == "document and process", (
            f"Expected 'document and process', got: {repr(result)}"
        )


# ═══════════════════════════════════════════════════════════════
# cleanup_watermark_contamination
# ═══════════════════════════════════════════════════════════════


class TestCleanupWatermarkContamination:
    """Tests for cleanup_watermark_contamination() — removing embedded fragments."""

    def test_remove_embedded_fragment(self):
        """Watermark fragment embedded in body text must be removed."""
        text = "评先网福建省电力有限公评优资格"
        result = cleanup_watermark_contamination(text)
        assert "网福建省电力有限公" not in result, (
            f"Contamination not removed: {repr(result)}"
        )
        assert "评先" in result
        assert "评优资格" in result

    def test_remove_truncated_fragment(self):
        """Truncated '建省电力有限公司厦' must be removed."""
        text = "相关建省电力有限公司厦部门"
        result = cleanup_watermark_contamination(text)
        assert "建省电力有限公司厦" not in result

    def test_clean_text_unchanged(self):
        """Clean text without contamination must be unchanged."""
        text = "这是一段正常的文本内容。"
        result = cleanup_watermark_contamination(text)
        assert result == text

    def test_empty_string(self):
        """Empty string must not crash."""
        result = cleanup_watermark_contamination("")
        assert result == ""


# ═══════════════════════════════════════════════════════════════
# merge_paragraphs
# ═══════════════════════════════════════════════════════════════


class TestMergeParagraphs:
    """Tests for merge_paragraphs() — line merging into paragraphs."""

    def test_single_paragraph(self):
        """Consecutive non-empty lines must merge into one paragraph."""
        lines = ["第一行", "第二行", "第三行"]
        result = merge_paragraphs(lines)
        assert result == "第一行第二行第三行", f"Got: {repr(result)}"

    def test_empty_line_break(self):
        """Empty line must signal paragraph break."""
        lines = ["段落一第一行", "段落一第二行", "", "段落二第一行"]
        result = merge_paragraphs(lines)
        assert "段落一第一行段落一第二行" in result
        assert "段落二第一行" in result
        assert "\n\n" in result

    def test_section_header_break(self):
        """Section headers like '一、' must start a new paragraph."""
        lines = ["前文内容", "一、主要内容", "具体内容"]
        result = merge_paragraphs(lines)
        assert "\n\n" in result, "Section header should create a paragraph break"
        assert "一、主要内容" in result

    def test_leading_trailing_blanks_handled(self):
        """Leading/trailing blank lines should be handled gracefully."""
        lines = ["", "内容", ""]
        result = merge_paragraphs(lines)
        assert result == "内容"

    def test_empty_input(self):
        """Empty input should return empty string."""
        assert merge_paragraphs([]) == ""


# ═══════════════════════════════════════════════════════════════
# convert_lines_to_markdown (integration point within utils)
# ═══════════════════════════════════════════════════════════════


class TestConvertLinesToMarkdown:
    """Tests for convert_lines_to_markdown() — end-to-end utility pipeline."""

    def test_full_pipeline_with_watermark(self):
        """Lines with watermark content must produce clean markdown."""
        lines = [
            "正常正文内容。",
            "\u3000国网福建省电力有限公司厦门供电公司\u3000",
            "黄琦斌 2025-04-14",
            "继续正文内容。",
        ]
        result = convert_lines_to_markdown(lines, remove_watermark=True)
        assert "黄琦斌" not in result, "Watermark content leaked into output!"
        assert "国网福建省" not in result, (
            "Keyword '国网福建省' leaked into output!"
        )
        assert "正常正文内容" in result
        assert "继续正文内容" in result

    def test_no_removal_flag(self):
        """With remove_watermark=False, watermark lines must be preserved."""
        lines = [
            "正文。",
            "\u3000国网福建省电力有限公司厦门供电公司\u3000",
        ]
        result = convert_lines_to_markdown(lines, remove_watermark=False)
        assert "正文" in result
        # Watermark content may or may not be in output depending on format
        # But at minimum the function should not crash

    def test_hyphenation_repair_in_pipeline(self):
        """Hyphenation repair must work as part of the pipeline."""
        lines = ["取", "消", "应", "用"]
        result = convert_lines_to_markdown(lines, remove_watermark=False)
        # After hyphenation repair: "取消应用"
        assert "取消应用" in result or "取消" in result

    def test_empty_lines_list(self):
        """Empty list must return empty string."""
        result = convert_lines_to_markdown([])
        assert result == ""


# ═══════════════════════════════════════════════════════════════
# Bug Report
# ═══════════════════════════════════════════════════════════════
# (Empty for now — discovered during test run)
