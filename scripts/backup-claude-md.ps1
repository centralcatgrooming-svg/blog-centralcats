# backup-claude-md.ps1 - Salin CLAUDE.md blog ke Google Drive.
#
# KENAPA ADA: repo blog ini PUBLIC, jadi CLAUDE.md sengaja masuk .gitignore
# (isinya App ID Meta, IG user ID, catatan bisnis). Konsekuensinya dokumen acuan
# terpenting repo ini TIDAK punya riwayat versi dan TIDAK ikut backup git -
# hilang bersama mesin ini kalau tak disalin ke tempat lain.
#
# Ini pengulangan pola yang sudah pernah menggigit di repo POS: skrip backup
# dulu di-.gitignore karena memuat password, lalu HILANG TOTAL saat pindah mesin
# sementara README-nya tetap mengklaim backup berjalan. Karena itu SKRIP INI
# ter-track git - yang dirahasiakan cukup ISI CLAUDE.md, bukan cara menyalinnya.
#
# Tujuan = folder Google Drive desktop yang tersinkron, sama dengan backup DB POS
# (scripts/backup-supabase.ps1 di repo central-cats-pos).
#
# Jalankan manual:  powershell -ExecutionPolicy Bypass -File scripts\backup-claude-md.ps1
# Override tujuan:  $env:CC_BACKUP_DEST = "D:\folder\lain"

$ErrorActionPreference = 'Stop'

$src = Join-Path (Split-Path $PSScriptRoot -Parent) 'CLAUDE.md'
if (-not (Test-Path $src)) { throw "CLAUDE.md tidak ditemukan di $src" }

# --- tujuan backup: cari folder Google Drive yang benar-benar ada -------------
function Cari-FolderDrive {
    if ($env:CC_BACKUP_DEST) { return $env:CC_BACKUP_DEST }
    $kandidat = @(
        "$env:USERPROFILE\Google Drive\Central Cats Backup",
        "$env:USERPROFILE\My Drive\Central Cats Backup",
        "G:\My Drive\Central Cats Backup",
        "G:\Drive Saya\Central Cats Backup"
    )
    foreach ($k in $kandidat) { if (Test-Path $k) { return $k } }
    return $null
}

$dest = Cari-FolderDrive
if (-not $dest) {
    throw "Folder Google Drive tak ditemukan. Pasang Google Drive desktop, atau set `$env:CC_BACKUP_DEST."
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$out = Join-Path $dest "blog-CLAUDE-$stamp.md"
Copy-Item $src $out -Force

# Verifikasi ukuran - Drive desktop kadang menulis stub 0 byte saat sync sibuk.
$a = (Get-Item $src).Length
$b = (Get-Item $out).Length
if ($a -ne $b) { throw "Salinan tidak utuh: sumber $a byte, salinan $b byte" }
Write-Output "OK: $out ($b byte)"

# --- retensi: simpan 8 salinan terakhir --------------------------------------
# Berkasnya kecil (~65 KB), jadi 8 salinan = setengah megabita. Cukup untuk
# menelusuri perubahan beberapa minggu ke belakang tanpa menumpuk selamanya.
Get-ChildItem $dest -Filter 'blog-CLAUDE-*.md' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 8 |
    ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Output "Dibuang (retensi): $($_.Name)"
    }
