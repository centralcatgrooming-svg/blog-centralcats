@echo off
REM ===========================================================================
REM  pasang-backup-claude-md.cmd - klik DUA KALI untuk MEMASANG backup mingguan
REM  CLAUDE.md blog ke Google Drive. Cukup dijalankan SEKALI.
REM
REM  Mendaftarkan scheduled task butuh hak Administrator, jadi berkas ini
REM  meminta elevasi sendiri (UAC muncul) - tak perlu klik kanan "Run as admin".
REM
REM  Setelah terpasang, backup jalan otomatis tiap Minggu 20:05.
REM ===========================================================================
setlocal

REM --- sudah admin? kalau belum, jalankan ulang diri sendiri dengan elevasi ---
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo Meminta hak Administrator... setujui jendela UAC yang muncul.
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

cd /d "%~dp0"

echo.
echo === Pasang backup mingguan CLAUDE.md blog ===
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-backup-claude-md.ps1"
if %errorlevel% neq 0 (
  echo.
  echo GAGAL memasang task. Baca pesan di atas.
  echo.
  pause
  exit /b 1
)

echo.
echo Menjalankan sekali untuk membuktikan backup-nya benar-benar bekerja...
powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'CentralCats-WeeklyBackup-BlogDocs'"
timeout /t 5 /nobreak >nul
powershell -NoProfile -Command "Get-ScheduledTaskInfo -TaskName 'CentralCats-WeeklyBackup-BlogDocs' | Select-Object LastRunTime, LastTaskResult, NextRunTime | Format-List"

echo.
echo ============================================================
echo  LastTaskResult 0 = berhasil.
echo  Cek hasilnya di folder Google Drive: Central Cats Backup
echo  Tekan tombol apa saja untuk menutup jendela ini.
echo ============================================================
pause >nul
