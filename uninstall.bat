@echo off
title Whisper Dictate — Uninstaller
color 0C
echo.
echo  Removing Whisper Dictate...

:: Kill running process
taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im python.exe  >nul 2>&1

:: Remove from startup
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WhisperDictate.lnk" >nul 2>&1

:: Remove app folder
rmdir /s /q "C:\dictate-app" >nul 2>&1

echo  Done! Whisper Dictate has been removed.
echo.
pause