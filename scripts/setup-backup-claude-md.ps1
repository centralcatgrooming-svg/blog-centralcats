# setup-backup-claude-md.ps1 - Daftarkan task mingguan untuk backup-claude-md.ps1.
#
# Jalankan SEKALI, sebagai Administrator:
#   powershell -ExecutionPolicy Bypass -File scripts\setup-backup-claude-md.ps1
#
# Jadwalnya sengaja disamakan dengan backup DB POS (Minggu 20:00) tapi digeser
# 5 menit supaya keduanya tidak berebut Google Drive sync di saat yang sama.
#
# `StartWhenAvailable` = kalau PC mati saat jamnya, task dikejar begitu PC hidup.
# Tanpa itu backup mingguan diam-diam terlewat setiap kali PC libur akhir pekan.

$ErrorActionPreference = 'Stop'

$nama = 'CentralCats-WeeklyBackup-BlogDocs'
$skrip = Join-Path $PSScriptRoot 'backup-claude-md.ps1'
if (-not (Test-Path $skrip)) { throw "Skrip tidak ditemukan: $skrip" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$skrip`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '20:05'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $nama -Action $action -Trigger $trigger `
    -Settings $settings -Description 'Backup CLAUDE.md blog ke Google Drive (dokumen gitignored).' -Force | Out-Null

Write-Output "Task '$nama' terdaftar - Minggu 20:05."
Write-Output "Uji sekarang tanpa menunggu jadwal:  Start-ScheduledTask -TaskName '$nama'"
