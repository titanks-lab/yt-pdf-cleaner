"""Shared test fixtures for YT-PDFCleaner tests.

All tests use real PDF files from /vault/raw/ and create temp copies
to ensure repeatability without modifying originals.
"""

import os
import shutil
import tempfile
import pymupdf
from pathlib import Path
from typing import Generator, Tuple

import pytest

# ── Real PDF paths ──────────────────────────────────────────────
VAULT_RAW = Path("/vault/raw")

WATERMARKED_PDF = Path("/tmp/test_watermarked.pdf")

NON_WATERMARKED_PDF = Path("/tmp/test_non_watermarked.pdf")

LARGE_WATERMARKED_PDF = Path("/tmp/test_large_watermarked.pdf")

# ── Helpers ──────────────────────────────────────────────────────


def check_pdf_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def create_empty_pdf(tmpdir: str) -> str:
    """Create a valid empty PDF (1 blank page)."""
    path = os.path.join(tmpdir, "empty.pdf")
    doc = pymupdf.open()
    doc.insert_page(-1, width=595, height=842)  # A4
    doc.save(path)
    doc.close()
    return path


def create_corrupted_pdf(tmpdir: str) -> str:
    """Create a corrupted/invalid PDF file (binary junk)."""
    path = os.path.join(tmpdir, "corrupted.pdf")
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\n% junk\n\xff\xfe\x00\x01corrupted data\x00")
    return path


def create_encrypted_pdf(tmpdir: str) -> str:
    """Create a password-protected PDF."""
    path = os.path.join(tmpdir, "encrypted.pdf")
    doc = pymupdf.open()
    doc.insert_page(-1, width=595, height=842)
    doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="secret", user_pw="secret")
    doc.close()
    return path


# ── Pytest fixtures ─────────────────────────────────────────────


@pytest.fixture(scope="function")
def tmp_workdir() -> Generator[str, None, None]:
    """Create a temporary working directory for test outputs."""
    with tempfile.TemporaryDirectory(prefix="ytpdf_test_") as tmpdir:
        yield tmpdir


@pytest.fixture(scope="session")
def watermarked_pdf_path() -> Path:
    """Path to a known watermarked PDF."""
    assert check_pdf_exists(WATERMARKED_PDF), (
        f"Watermarked PDF not found: {WATERMARKED_PDF}"
    )
    return WATERMARKED_PDF


@pytest.fixture(scope="session")
def non_watermarked_pdf_path() -> Path:
    """Path to a known non-watermarked PDF."""
    assert check_pdf_exists(NON_WATERMARKED_PDF), (
        f"Non-watermarked PDF not found: {NON_WATERMARKED_PDF}"
    )
    return NON_WATERMARKED_PDF


@pytest.fixture(scope="session")
def large_watermarked_pdf_path() -> Path:
    """Path to a large watermarked PDF (~1.4 MB, 63 pages)."""
    assert check_pdf_exists(LARGE_WATERMARKED_PDF), (
        f"Large watermarked PDF not found: {LARGE_WATERMARKED_PDF}"
    )
    return LARGE_WATERMARKED_PDF


@pytest.fixture
def empty_pdf(tmp_workdir: str) -> str:
    """Create an empty (blank) PDF for testing."""
    return create_empty_pdf(tmp_workdir)


@pytest.fixture
def corrupted_pdf(tmp_workdir: str) -> str:
    """Create a corrupted PDF for testing."""
    return create_corrupted_pdf(tmp_workdir)


@pytest.fixture
def encrypted_pdf(tmp_workdir: str) -> str:
    """Create an encrypted PDF for testing."""
    return create_encrypted_pdf(tmp_workdir)


@pytest.fixture
def watermarked_copy(tmp_workdir: str, watermarked_pdf_path: Path) -> str:
    """A writable copy of the watermarked PDF (original is not modified)."""
    dst = os.path.join(tmp_workdir, "watermarked_copy.pdf")
    shutil.copy2(str(watermarked_pdf_path), dst)
    return dst


@pytest.fixture
def non_watermarked_copy(tmp_workdir: str, non_watermarked_pdf_path: Path) -> str:
    """A writable copy of the non-watermarked PDF."""
    dst = os.path.join(tmp_workdir, "non_watermarked_copy.pdf")
    shutil.copy2(str(non_watermarked_pdf_path), dst)
    return dst


def pdf_has_watermark_content(pdf_path: str) -> bool:
    """Check if a PDF has watermark stream content after processing."""
    doc = pymupdf.open(pdf_path)
    for pi in range(len(doc)):
        page = doc[pi]
        for xref in page.get_contents():
            stream = doc.xref_stream(xref)
            if stream:
                if b"0.6 0.6 0.6 rg" in stream and b"0.93969" in stream:
                    doc.close()
                    return True
    doc.close()
    return False
