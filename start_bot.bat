@echo off
title Oracle Free Tier Auto Retry Bot
echo ========================================================
echo  Oracle Cloud Always Free - ARM VM Auto-Retry Launcher
echo ========================================================
echo.
cd /d "%~dp0"
python auto_retry_launch.py
pause
