@echo off
REM ============================================
REM YT-PDFCleaner — Windows Build Script
REM ============================================
REM Builds a portable distribution in dist/YT-PDFCleaner/
REM
REM Prerequisites:
REM   1. Python 3.13 installed and in PATH
REM   2. Dependencies installed:
REM        pip install -r requirements.txt
REM
REM Usage:
REM   build\build.bat          # Build portable distribution
REM   build\build.bat --clean  # Clean cache and rebuild
REM   build\build.bat --verify # Only verify existing build
REM ============================================

setlocal enabledelayedexpansion

cd /d "%~dp0.."

if "%1" == "--verify" (
    echo [INFO] Verifying existing build...
    if exist "dist\YT-PDFCleaner\YT-PDFCleaner.exe" (
        echo [OK] dist\YT-PDFCleaner\YT-PDFCleaner.exe found
        dir /b "dist\YT-PDFCleaner\_internal\*.pyd" 2>nul | find /c /v "" >nul && (
            echo [OK] Internal libraries present
        ) || (
            echo [WARN] No .pyd files found in _internal
        )
    ) else (
        echo [ERROR] Build not found. Run build.bat first.
        exit /b 1
    )
    goto :eof
)

echo ============================================
echo  YT-PDFCleaner — Windows Build
echo ============================================
echo.

if "%1" == "--clean" (
    echo [INFO] Cleaning previous builds...
    if exist "build" rmdir /s /q "build"
    if exist "dist" rmdir /s /q "dist"
    if exist "YT-PDFCleaner.spec" del /q "YT-PDFCleaner.spec"
    echo [OK] Cleaned.
    echo.
)

echo [INFO] Installing/updating PyInstaller...
pip install -q pyinstaller

echo [INFO] Building YT-PDFCleaner portable distribution...
pyinstaller ^
    --name "YT-PDFCleaner" ^
    --onedir ^
    --console ^
    --clean ^
    --noconfirm ^
    --exclude-module tkinter ^
    --exclude-module test ^
    --exclude-module unittest ^
    --exclude-module tcl ^
    --hidden-import ttkbootstrap ^
    --hidden-import ttkbootstrap.constants ^
    --hidden-import ttkbootstrap.dialogs ^
    --hidden-import ttkbootstrap.toast ^
    --hidden-import ttkbootstrap.tableview ^
    --hidden-import ttkbootstrap.widgets ^
    --hidden-import PIL ^
    main.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed with error code %errorlevel%
    exit /b %errorlevel%
)

echo.
echo ============================================
echo  Build complete!
echo  Output: dist\YT-PDFCleaner\
echo  Executable: dist\YT-PDFCleaner\YT-PDFCleaner.exe
echo ============================================

if exist "dist\YT-PDFCleaner\YT-PDFCleaner.exe" (
    echo [OK] Build verified: executable exists
) else (
    echo [ERROR] Build verification failed: executable not found
    exit /b 1
)

goto :eof
