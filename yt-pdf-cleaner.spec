# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for YT-PDFCleaner v1.3.0 — Windows build.

Usage:
    pyinstaller yt-pdf-cleaner.spec

Output: dist/YT-PDFCleaner.exe
"""

import sys
import os
from pathlib import Path

BLOCK_CIPHER = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include all GUI resource files (icons)
        ('gui/icon.ico', 'gui'),
        ('gui/icon.png', 'gui'),
        ('gui/icon_dialog_check.png', 'gui'),
        ('gui/icon_dialog_warn.png', 'gui'),
    ],
    hiddenimports=[
        'ttkbootstrap',
        'ttkbootstrap.localization',
        'PIL',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'email',
        'http',
        'urllib',
        'xml',
        'pydoc',
        'doctest',
        'distutils',
        'lib2to3',
        'concurrent',
        'multiprocessing',
        'asyncio',
        'pdb',
        'profile',
        'pstats',
        'cProfile',
        'bz2',
        'lzma',
        'zipfile',
        'tarfile',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YT-PDFCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Windowed app (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/icon.ico',    # Application icon
)

# Also create a one-folder version for easier debugging
if '--onedir' in sys.argv:
    COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='YT-PDFCleaner',
    )
