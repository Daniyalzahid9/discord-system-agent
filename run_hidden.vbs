Set WshShell = CreateObject("WScript.Shell")
strCurDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurDir
WshShell.Run Chr(34) & strCurDir & "\.venv\Scripts\pythonw.exe" & Chr(34) & " bot.py", 0, False
