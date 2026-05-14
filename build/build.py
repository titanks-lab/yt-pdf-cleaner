#!/usr/bin/env python3
"""PyInstaller build script for YT-PDFCleaner.

Builds a portable Windows distribution (single-folder) from main.py.

Usage:
    python build/build.py           # Build dist/YT-PDFCleaner/
    python build/build.py --clean   # Clean cache before building
"""
import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist", "YT-PDFCleaner")


def build(clean: bool = False) -> None:
    """Run PyInstaller to build the portable distribution."""
    os.chdir(PROJECT_ROOT)

    if clean:
        for d in ["build", "dist"]:
            path = os.path.join(PROJECT_ROOT, d)
            if os.path.isdir(path):
                print(f"Cleaning {d}/ ...")
                shutil.rmtree(path)
        spec_file = os.path.join(PROJECT_ROOT, "YT-PDFCleaner.spec")
        if os.path.isfile(spec_file):
            os.remove(spec_file)

    print("==> Building YT-PDFCleaner with PyInstaller ...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "YT-PDFCleaner",
        "--onedir",                     # Single-folder (portable)
        "--console",                    # Keep console for CLI mode
        "--clean",
        "--noconfirm",
        # Exclude unnecessary modules
        "--exclude-module", "tkinter",
        "--exclude-module", "test",
        "--exclude-module", "unittest",
        "--exclude-module", "tcl",
        # Hidden imports for ttkbootstrap
        "--hidden-import", "ttkbootstrap",
        "--hidden-import", "ttkbootstrap.constants",
        "--hidden-import", "ttkbootstrap.dialogs",
        "--hidden-import", "ttkbootstrap.toast",
        "--hidden-import", "ttkbootstrap.tableview",
        "--hidden-import", "ttkbootstrap.widgets",
        "--hidden-import", "PIL",
        # Data files: ttkbootstrap themes
        "--add-data", f"ttkbootstrap{os.pathsep}ttkbootstrap",
        "main.py",
    ]
    subprocess.check_call(cmd)
    print(f"\n==> Build complete! Output: {DIST_DIR}")


def verify() -> bool:
    """Verify the build by checking key files and importing pymupdf."""
    print("\n==> Verifying build ...")
    exe_path = os.path.join(DIST_DIR, "YT-PDFCleaner.exe")
    if not os.path.isfile(exe_path):
        print(f"ERROR: {exe_path} not found!")
        return False
    print(f"  ✅ {exe_path}")

    # Check key libraries are bundled
    libs = ["pymupdf", "ttkbootstrap"]
    lib_dir = os.path.join(DIST_DIR, "_internal")
    if os.path.isdir(lib_dir):
        found = os.listdir(lib_dir)
        for lib in libs:
            if any(lib.replace("-", "_") in f for f in found):
                print(f"  ✅ {lib} bundled")
            else:
                print(f"  ⚠️  {lib} not verified in _internal/ (may be included anyway)")
    else:
        print("  ⚠️  No _internal/ directory found (might be PyInstaller version difference)")

    return True


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Build YT-PDFCleaner portable distribution")
    parser.add_argument("--clean", action="store_true", help="Clean cache before building")
    parser.add_argument("--verify", action="store_true", help="Only verify existing build")
    args = parser.parse_args()

    if args.verify:
        sys.exit(0 if verify() else 1)

    build(clean=args.clean)
    verify()


if __name__ == "__main__":
    main()
