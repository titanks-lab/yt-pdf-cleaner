"""Utility functions for PDF watermark removal and Markdown conversion.

Provides helper functions for:
- Filtering watermark lines from extracted text
- Merging paragraphs with proper sentence-boundary detection
- Repairing cross-page hyphenation and page-break issues
"""

import re
from typing import List


# Watermark keywords — a line is flagged if it contains MULTIPLE indicators.
# The tracking watermark always combines these keywords with dates and
# ideographic spaces (\u3000) in the same line.
WATERMARK_KEYWORDS: List[str] = [
    "国网福建省",
    "厦门供电",
    "远通分公司",
    "黄琦斌",
]

# Secondary indicators that boost confidence
WATERMARK_SECONDARY: List[str] = [
    "远通",
    "琦斌",
    "省电力有限公司厦",
    "门供电公司",
    "通分公司",
]

# Truncated watermark fragments — these appear when the watermark text is
# split across PDF content streams. They are DISTINCTIVE (not found in body
# text) because the body always uses the full "国网福建省" form.
# NOTE: "建省电力", "网福建省电力有限公", "福建省电力有限公" etc.
# are NOT used because they match legitimate body text substrings.
WATERMARK_FRAGMENTS: List[str] = [
    "建省电力有限公司厦",  # truncated "福建省电力有限公司厦门" → "建省电力有限公司厦"
]

# Date pattern matching watermark dates like 2025-04-14
WATERMARK_DATE_PATTERN: re.Pattern = re.compile(r"\d{4}-\d{2}-\d{2}")

# Ideographic space (common in watermark padding)
IDEOGRAPHIC_SPACE = "\u3000"

# Page number markers like "— 1 —", "— 2 —" (em-dash + number + em-dash).
# Surrounding newlines are consumed so cross-page text can merge properly.
# e.g. "取\n— 2 —\n消" → "取消"
PAGE_NUMBER_PATTERN: re.Pattern = re.compile(r"\n?—\s*\d+\s*—\n?")


def is_watermark_line(line: str) -> bool:
    """Check if a line of text appears to be a tracking watermark.

    Detection strategy — a line is a watermark if it satisfies at least ONE of:
    1. Contains ideographic space (\u3000) AND any watermark keyword
    2. Contains at least TWO different watermark keywords
    3. Has date pattern AND ideographic space in the same line
    4. Contains a watermark keyword AND a date pattern
       (but exempts known legitimate body text like department names)
    5. Is a truncated fragment containing known watermark substrings
       but NOT resembling normal sentence text

    Args:
        line: The text line to check.

    Returns:
        True if the line is likely a watermark, False otherwise.
    """
    # Quick checks
    has_keyword = any(kw in line for kw in WATERMARK_KEYWORDS)
    has_secondary = any(kw in line for kw in WATERMARK_SECONDARY)
    has_fragment = any(kw in line for kw in WATERMARK_FRAGMENTS)
    has_date = bool(WATERMARK_DATE_PATTERN.search(line))
    has_ideosp = IDEOGRAPHIC_SPACE in line

    # Exempt known legitimate body text patterns
    # These are document header/footer lines, NOT watermarks
    if line.strip() in (
        "国网福建省电力有限公司部门文件",
        "国网福建省电力有限公司企管部（体改办）",
        "国网福建省电力有限公司办公室",
    ):
        return False

    # Rule 1: Ideographic space + any keyword → definitely watermark
    # The body text never has \u3000 alongside these keywords
    if has_ideosp and (has_keyword or has_secondary):
        return True

    # Rule 2: At least two different watermark keywords
    keyword_matches = [kw for kw in WATERMARK_KEYWORDS if kw in line]
    if len(keyword_matches) >= 2:
        return True

    # Rule 3: Keyword + secondary indicator
    if has_keyword and has_secondary:
        return True

    # Rule 4: Keyword + date (with multi-indicator evidence)
    if has_keyword and has_date:
        return True

    # Rule 5: Single keyword but suspicious context
    # e.g., "建省电力有限公司厦" or "2025-04-14    国网"
    # These are truncated watermark fragments
    secondary_matches = [kw for kw in WATERMARK_SECONDARY if kw in line]
    if len(secondary_matches) >= 2 and has_date:
        return True

    # Rule 6: Ideographic space alone (watermark padding characters)
    # Body text never has \u3000
    if has_ideosp and len(line.strip()) > 0:
        return True

    # Rule 7: Truncated watermark fragments
    # These are distinctive patterns that ONLY appear in truncated watermarks
    if has_fragment:
        return True

    return False


def filter_watermark_lines(lines: List[str]) -> List[str]:
    """Filter out watermark lines from a list of text lines.

    Args:
        lines: List of text lines (strings).

    Returns:
        List of lines with watermark lines removed.
    """
    return [l for l in lines if not is_watermark_line(l)]


def strip_page_numbers(text: str) -> str:
    """Remove page number markers like '— 1 —' from text.

    These markers appear between pages in PDF text extraction and interfere
    with cross-page text continuity (e.g., "取\n— 2 —\n消" should become "取消").
    Surrounding newlines are also removed to allow text on either side to merge.

    Args:
        text: The full text with potential page number markers.

    Returns:
        Text with page number markers and their surrounding newlines removed.
    """
    return PAGE_NUMBER_PATTERN.sub("", text)


def repair_hyphenation(text: str) -> str:
    """Repair cross-page/line hyphenation and character breaks.

    Handles:
    - English word hyphenation: "docu-\nment" → "document"
    - Chinese character split across pages: "取\n消" → "取消"
    - Removes page number markers between split characters

    Args:
        text: The full text with potential hyphenation breaks.

    Returns:
        Text with hyphenation breaks and page separators repaired.
    """
    # Step 1: Remove page number markers so cross-page text can merge
    text = strip_page_numbers(text)

    # Step 2: English hyphenation: word-hyphen-newline-continuation
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Step 3: CJK character split across pages (explicit hyphen)
    text = re.sub(
        r"([\u4e00-\u9fff\u3400-\u4dbf])-\n([\u4e00-\u9fff\u3400-\u4dbf])",
        r"\1\2",
        text,
    )

    # Step 4: CJK character split across pages (no hyphen, just newline)
    text = re.sub(
        r"([\u4e00-\u9fff])\n([\u4e00-\u9fff])",
        r"\1\2",
        text,
    )

    return text


# Pattern to clean up watermark contamination that gets embedded in body text.
# These patterns are specific enough to not match legitimate document text.
WATERMARK_CONTAMINATION_PATTERNS: List[re.Pattern] = [
    # "网福建省电力" NOT preceded by "国" — only appears in watermark contamination
    re.compile(r"(?<!国)网福建省电力有限公司?[^。\n]{0,20}?(?=[\u4e00-\u9fff])"),
    # "建省电力有限公司厦" — unique truncated watermark
    re.compile(r"建省电力有限公司厦"),
]


def cleanup_watermark_contamination(text: str) -> str:
    """Remove watermark contamination fragments from final markdown text.

    After paragraph merging, watermark fragments that survived line-level
    filtering may be embedded in body text (e.g., "评先网福建省电力有限公评优资格").
    This function removes such contamination using targeted regex patterns.

    Args:
        text: The merged markdown text.

    Returns:
        Cleaned text with watermark contamination removed.
    """
    for pattern in WATERMARK_CONTAMINATION_PATTERNS:
        text = pattern.sub("", text)
    return text


def merge_paragraphs(lines: List[str]) -> str:
    """Merge lines into paragraphs based on sentence boundaries.

    - Consecutive non-empty lines are joined into a single paragraph.
    - An empty line signals a paragraph break.
    - A line starting with a section header pattern (e.g., "一、", "二、")
      starts a new paragraph.

    Args:
        lines: List of cleaned text lines (watermark already filtered).

    Returns:
        A string with paragraphs separated by double newlines.
    """
    paragraphs: List[str] = []
    current_para: List[str] = []

    def _flush():
        nonlocal current_para
        if current_para:
            paragraphs.append("".join(current_para))
            current_para = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Empty line is a paragraph break
            _flush()
            continue

        # Check if line starts a section header (Chinese numbered sections)
        # These naturally start new paragraphs
        if re.match(r"^[一二三四五六七八九十]+[、．.]", stripped):
            _flush()

        current_para.append(stripped)

    # Don't forget the last paragraph
    _flush()

    # Join paragraphs with double newlines
    return "\n\n".join(paragraphs)


def convert_lines_to_markdown(
    lines: List[str], remove_watermark: bool = True
) -> str:
    """Convert raw extracted PDF lines to clean Markdown text.

    Processing pipeline:
    1. Filter out watermark lines (if enabled)
    2. Repair hyphenation and cross-page breaks
    3. Merge into paragraphs with proper structure

    Args:
        lines: Raw text lines from PDF extraction.
        remove_watermark: Whether to filter watermark lines. Default True.

    Returns:
        Clean Markdown text with proper paragraph breaks.
    """
    if remove_watermark:
        lines = filter_watermark_lines(lines)

    # Join all lines and repair hyphenation
    raw_text = "\n".join(lines)
    raw_text = repair_hyphenation(raw_text)

    # Split back into lines after hyphenation repair
    cleaned_lines = raw_text.split("\n")

    # Filter again for any remaining watermark content that may have
    # been exposed after joining/splitting
    if remove_watermark:
        cleaned_lines = filter_watermark_lines(cleaned_lines)

    # Remove empty lines at start/end
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    # Merge into paragraphs
    markdown_text = merge_paragraphs(cleaned_lines)

    # Post-process: remove any watermark contamination that got embedded
    # in body text after paragraph merging
    markdown_text = cleanup_watermark_contamination(markdown_text)

    return markdown_text
