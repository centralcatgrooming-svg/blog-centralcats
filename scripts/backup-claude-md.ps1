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

# --- nama berkas: WAJIB memuat penanda MESIN ---------------------------------
# DUA mesin (PC toko + laptop) menulis ke folder Drive yang SAMA, dan jadwalnya
# IDENTIK (Minggu 20:05 di keduanya) -> tanpa penanda ini namanya bertabrakan
# SETIAP MINGGU. Bukan teori: "blog-CLAUDE-20260906-2005 (1).md" di Drive adalah
# Google Drive menyelesaikan tabrakan itu sendiri.
#
# Lebih berbahaya dari sekadar nama: kedua mesin menyimpan CLAUDE.md yang
# BERBEDA (terukur 16 Sep 2026 - PC toko 74,5 KB, laptop 71,3 KB versi lebih
# lama). Tanpa penanda mesin, memulihkan dari salinan yang salah = mundur
# beberapa minggu tanpa ada yang sadar.
#
# Bentuk namanya sengaja SERAGAM dengan backup DB POS (backup-supabase.ps1).
# Mesin di luar peta jatuh ke COMPUTERNAME apa adanya - SENGAJA tidak menebak,
# karena label yang salah lebih menyesatkan daripada label yang jelek.
$PETA_MESIN = @{
    'LAPTOP-3V5NK6SJ' = 'Laptop'
    'DESKTOP-1N6BCAH' = 'PC Toko'
    # Mesin BARU: tambahkan barisnya di sini. Fallback di bawah lolos tanpa
    # galat, jadi nama jelek TIDAK akan memberi tahu siapa pun bahwa petanya
    # belum lengkap.
}
$mesin = if ($PETA_MESIN.ContainsKey($env:COMPUTERNAME)) { $PETA_MESIN[$env:COMPUTERNAME] }
         else { $env:COMPUTERNAME }

$stamp = Get-Date -Format 'yyyy-MM-dd HHmm'
$out = Join-Path $dest "blog-CLAUDE-$stamp - $mesin.md"
Copy-Item $src $out -Force

# Verifikasi ukuran - Drive desktop kadang menulis stub 0 byte saat sync sibuk.
$a = (Get-Item $src).Length
$b = (Get-Item $out).Length
if ($a -ne $b) { throw "Salinan tidak utuh: sumber $a byte, salinan $b byte" }
Write-Output "OK: $out ($b byte)"

# --- retensi: 8 salinan terakhir PER MESIN -----------------------------------
# Berkasnya kecil (~74 KB), jadi 8 salinan per mesin tetap di bawah 1,2 MB.
#
# PER MESIN, bukan 8 total: dua mesin menulis ke folder yang sama, jadi "8
# terakhir" dulu berarti ~4 minggu per mesin, bukan 8. Kelas kekeliruan yang
# sama dengan retensi backup DB POS sebelum 14 Sep 2026 ("jumlah berkas" diam-
# diam bukan lagi "lama waktu" begitu penulisnya lebih dari satu).
#
# 🔴 Diurutkan berdasarkan NAMA, BUKAN LastWriteTime. Copy-Item MEMPERTAHANKAN
# timestamp sumber, jadi semua salinan bertanggal "kapan CLAUDE.md terakhir
# diubah" - bukan "kapan ia di-backup". Terukur 16 Sep 2026: kedelapan salinan
# di Drive bertimestamp 2 Sep, padahal dibuat dari 2 Sep s/d 14 Sep. Artinya
# urutan lama praktis sewenang-wenang, dan saat CLAUDE.md tak berubah
# berminggu-minggu (kejadian normal) pemangkas bisa membuang salinan TERBARU
# dan menyisakan yang lama. Stempel waktu backup yang jujur hanya ada di NAMA.
$SIMPAN = 8

function Mesin-Dari-Nama($nama) {
    # "blog-CLAUDE-2026-09-20 2005 - PC Toko.md" -> "PC Toko"
    # Nama WARISAN (sebelum 16 Sep 2026, tanpa " - ") dikelompokkan sendiri
    # supaya ia tak saling memangkas dengan salinan bermesin. Kelompoknya tak
    # akan tumbuh lagi, jadi ia luruh sendiri tanpa perlu disentuh.
    $tanpaExt = [IO.Path]::GetFileNameWithoutExtension($nama)
    $i = $tanpaExt.LastIndexOf(' - ')
    if ($i -lt 0) { return '(warisan)' }
    return $tanpaExt.Substring($i + 3)
}

Get-ChildItem $dest -Filter 'blog-CLAUDE-*.md' |
    Group-Object { Mesin-Dari-Nama $_.Name } |
    ForEach-Object {
        $_.Group |
            Sort-Object Name -Descending |
            Select-Object -Skip $SIMPAN |
            ForEach-Object {
                Remove-Item $_.FullName -Force
                Write-Output "Dibuang (retensi, $($_.Name))"
            }
    }
