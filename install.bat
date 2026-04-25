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
pip install faster-whisper sounddevice numpy keyboard pyautogui pystray pillow
echo  Packages installed ✓

:: Create app folder
echo.
echo [3/4] Setting up app folder...
if not exist "C:\dictate-app" mkdir "C:\dictate-app"
copy /Y "%~dp0dictate.py" "C:\dictate-app\dictate.py" >nul
copy /Y "%~dp0run.bat"    "C:\dictate-app\run.bat"    >nul
echo  Files copied ✓

:: Add to startup
echo.
echo [4/4] Adding to Windows startup...
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set PYTHON_PATH=
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\shortcut.vbs"
echo sLinkFile = "%STARTUP%\WhisperDictate.lnk" >> "%TEMP%\shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\shortcut.vbs"
echo oLink.TargetPath = "%PYTHON_PATH%" >> "%TEMP%\shortcut.vbs"
echo oLink.Arguments = "C:\dictate-app\dictate.py" >> "%TEMP%\shortcut.vbs"
echo oLink.WindowStyle = 7 >> "%TEMP%\shortcut.vbs"
echo oLink.Description = "Whisper Dictate" >> "%TEMP%\shortcut.vbs"
echo oLink.Save >> "%TEMP%\shortcut.vbs"
cscript //nologo "%TEMP%\shortcut.vbs"
echo  Added to startup ✓

echo.
echo  ================================================
echo   Installation Complete!
echo.
echo   First run will download the Whisper model
echo   (~74MB, one time only).
echo.
echo   HOW TO USE:
echo   - App starts automatically with Windows
echo   - Green icon in system tray = ready
echo   - Hold backtick key [  `  ] to record
echo   - Release to transcribe and type
echo   - Right-click tray icon to quit
echo  ================================================
echo.
echo  Launching app now...
timeout /t 2 >nul
start "" python "C:\dictate-app\dictate.py"
echo.
pause