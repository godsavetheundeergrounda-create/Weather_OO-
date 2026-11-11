@echo off
setlocal
chcp 65001 >nul
title Weather Aggregator - Create Desktop Shortcut
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_desktop_shortcut.ps1"
exit /b %ERRORLEVEL%
