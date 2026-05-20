@echo off
title Whisper Dictate — Installer
color 0A
echo.
echo  ================================================
echo   Whisper Dictate — Auto Installer
echo   Free speech-to-text for Windows
echo  ================================================
echo.

:: Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python not found. Installing Python 3.12...
    winget install --id=Python.Python.3.12 -e --source winget
    echo  Please CLOSE and REOPEN this window after Python installs, then run install.bat again.
    pause
    exit
) else (
    echo  Python found ✓
)

:: Install pip packages
echo.
echo [2/4] Installing required packages...
pip install faster-whisper sounddevice numpy keyboard pyautogui pystray pillow pyperclip nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12
echo  Packages installed ✓

:: App runs from current directory
echo.
echo [3/4] App will run from current folder ✓

:: App will not be added to startup

echo.
echo  ================================================
echo   Installation Complete!
echo.
echo   First run will download the Whisper model
echo   (~3GB, one time only).
echo.
echo   HOW TO USE:
echo   - App can be run via run.bat or python dictate.py
echo   - Green icon in system tray = ready
echo   - Hold backtick key [  `  ] to record
echo   - Release to transcribe and type
echo   - Right-click tray icon to quit
echo  ================================================
echo.
echo  Launching app now...
timeout /t 2 >nul
start "" python "%~dp0dictate.py"
echo.
pause