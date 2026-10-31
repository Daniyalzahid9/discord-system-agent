@echo off
title Install Discord Agent to Windows Startup
cd /d "%~dp0"

set "TARGET_SCRIPT=%~dp0run_hidden.vbs"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DiscordSystemAgent.lnk"

powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%TARGET_SCRIPT%\"'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

echo [OK] Discord System Agent shortcut created in Windows Startup folder:
echo %SHORTCUT_PATH%
echo The bot will now start silently in the background whenever you log into Windows!
pause
