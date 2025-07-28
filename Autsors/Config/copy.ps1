$sourceFile = "C:\DB_srv\13.11..2024\Outsource.db"  # Укажите путь к вашему файлу
$backupFolder = "C:\Users\A.A.Fedorov\Work folders\Documents\w"  # Укажите папку для резервных копий
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path -Path $backupFolder -ChildPath ("file_" + $timestamp + ".db")

Copy-Item -Path $sourceFile -Destination $backupFile
pause


