@echo off
REM ====================================================================
REM  YT-PDFCleaner — Windows Build Script
REM  Builds a standalone .exe with PyInstaller
REM ====================================================================
TITLE YT-PDFCleaner Builder

echo ========================================
echo  YT-PDFCleaner — Windows Build
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found! Please install Python 3.10+ from python.org
    echo        Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)

REM Generate icons (Pillow required)
echo [2/3] Generating icons...
python gui/generate_icons.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Icon generation failed, using existing icons...
)

REM Build .exe
echo [3/3] Building executable...
pyinstaller yt-pdf-cleaner.spec --clean
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build successful!
echo ========================================
echo  Output: dist\YT-PDFCleaner.exe
echo.
echo  Double-click YT-PDFCleaner.exe to run.
echo ========================================
pause
