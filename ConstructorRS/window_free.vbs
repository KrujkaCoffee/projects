Set WshShell = CreateObject("WScript.Shell")

args = ""
For i = 0 To WScript.Arguments.Count - 1
args = args & " " & WScript.Arguments(i)
Next

cmd = Chr(34) & ".\remote_run.bat" & Chr(34) & args

WshShell.Run cmd, 0
Set WshShell = Nothing