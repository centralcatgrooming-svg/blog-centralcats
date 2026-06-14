# Central Cat's Blog (Hugo + GitHub Pages)

Blog statis untuk `blog.centralcats.id`. Gratis, cepat, aman. Tulis artikel dalam
Markdown → commit ke GitHub → otomatis tayang. Situs utama `centralcats.id` menarik
daftar artikel dari feed `index.json`.

## Cara setup (sekali saja)

### 1. Buat repo di GitHub
- Buat repository baru, nama: **blog-centralcats** (boleh Public).
- Jangan centang "Add a README".

### 2. Upload isi folder ini
- Buka repo → **Add file → Upload files**.
- Seret **semua isi** folder ini (termasuk folder `content`, `layouts`, `.github`,
  file `hugo.toml`, dll). Pastikan `.github/workflows/hugo.yml` ikut terupload.
- Commit.

### 3. Aktifkan GitHub Pages
- Repo → **Settings → Pages**.
- Bagian **Build and deployment → Source**: pilih **GitHub Actions**.

### 4. Tunggu build
- Buka tab **Actions**. Workflow "Deploy Hugo ke GitHub Pages" akan jalan.
- Setelah hijau (≈1–2 menit), situs sudah ter-deploy.

### 5. Arahkan domain (di Hostinger)
- hPanel → **Domain → DNS / Nameserver** (DNS Zone Editor) untuk `centralcats.id`.
- Tambah record:
  - **Type:** CNAME
  - **Name / Host:** `blog`
  - **Target / Points to:** `centralcatgrooming-svg.github.io`
  - **TTL:** default
- Tunggu propagasi (biasanya menit–jam).
- Repo → Settings → Pages → **Custom domain** sudah otomatis `blog.centralcats.id`
  (dari file `static/CNAME`). Centang **Enforce HTTPS** bila sudah muncul.

## Cara menulis artikel baru
1. Masuk folder kategori yang sesuai: `content/kesehatan-hewan/`, `content/berita-tren/`,
   `content/bisnis-hewan/`, atau `content/panduan-tips/`.
2. **Add file → Create new file**, nama: `judul-artikel.md`.
3. Isi seperti contoh:
   ```
   +++
   title = "Judul Artikel"
   date = 2026-06-14T09:00:00+07:00
   categories = ["Kesehatan Kucing"]   # ini = SUBKATEGORI
   tags = ["kucing", "kesehatan"]
   summary = "Ringkasan singkat 1–2 kalimat."
   images = ["https://.../gambar.jpg"]  # opsional
   +++

   Isi artikel dalam Markdown.
   ```
4. Commit. Build jalan otomatis, artikel langsung tayang.

> **Kategori utama** ditentukan oleh **folder** tempat file disimpan.
> **Subkategori** ditentukan oleh field `categories` di front matter.

## Integrasi ke situs utama
Feed tersedia di `https://blog.centralcats.id/index.json`.
Gunakan file `blog-section-centralcats.html` (versi JSON) untuk menampilkannya di
`centralcats.id`.
