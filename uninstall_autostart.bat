@echo off
title Uninstall Discord Agent from Windows Startup
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DiscordSystemAgent.lnk"

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [OK] Removed startup shortcut from Windows Startup.
) else (
    echo [INFO] Startup shortcut was not present.
)
pause
