# Central Cat's News

Blog resmi **Central Cat's** — grooming, petshop, dan cat hotel kucing di Tangerang
(Pasar Kemis & Rajeg). Situs statis Hugo yang tayang di **https://blog.centralcats.id**.

> 📖 **Aturan kerja lengkap ada di [`CLAUDE.md`](CLAUDE.md)** — visi & misi, aturan performa,
> checklist SEO, larangan konten/kesehatan, dan rincian tiap otomasi. README ini hanya
> orientasi cepat. Untuk tugas UI/fitur, baca juga `.ai/ROADMAP.md`.

---

## Stack & alur deploy

| | |
|---|---|
| Generator | **Hugo Extended 0.147.0** (`hugo.toml`) |
| Hosting | GitHub Pages, domain custom `blog.centralcats.id` (`static/CNAME`) |
| Deploy | `.github/workflows/hugo.yml` — otomatis tiap **push ke `main`** |
| Build produksi | `hugo --gc --minify --baseURL "https://blog.centralcats.id/"` |

Alur normal: **commit → push ke `main` → build jalan (~1–2 menit) → tayang.**
Artikel dari draf AI masuk lewat **Pull Request** dulu (lihat Otomasi di bawah).

## Struktur folder

```
content/           artikel (folder = KATEGORI UTAMA)
  berita-tren/  kesehatan-hewan/  bisnis-hewan/  panduan-tips/
  _index.md    cari.md    tentang.md
layouts/           template Hugo (baseof, index, single, card, share, hewan/…)
assets/js/         JS yang di-INLINE ke halaman (share.js, analytics.js)
static/            file disajikan apa adanya (images/, CNAME, robots.txt, verifikasi)
scripts/           otomasi Python (draf AI, notifikasi, IndexNow, IG, katalog)
tests/             Vitest untuk assets/js/
```

## Cara menulis artikel baru

1. Pilih folder kategori yang sesuai di `content/`.
2. Buat file `slug-deskriptif.md` (huruf kecil, tanda hubung).
3. Front matter standar:

```toml
+++
title = "Judul Artikel yang Jelas dan Menarik"
date = 2026-08-15T09:00:00+07:00
draft = false
author = "Team Central Cat's"          # opsional, ini defaultnya
categories = ["Kesehatan Kucing"]      # = SUBKATEGORI
tags = ["kucing", "kesehatan", "bulu"]
hewan = ["kucing"]                     # taxonomy Indeks Hewan A-Z (huruf kecil)
summary = "Ringkasan 1–2 kalimat. Dipakai juga sebagai meta description SEO (maks ~155 karakter)."
images = ["/images/nama-gambar.webp"]  # gambar unggulan; WebP ≤1200px, taruh di static/images/

[[faq]]                                # opsional, 3–5 tanya-jawab → JSON-LD FAQPage
q = "Pertanyaan yang sering ditanyakan?"
a = "Jawaban singkat dan jelas."
+++

Paragraf pembuka langsung menjawab inti pertanyaan (gaya *answer-first*).
Isi artikel pakai H2/H3 berurutan.
```

**Kategori utama = folder. Subkategori = field `categories`. `hewan` = taxonomy Indeks A-Z.**

Sebelum commit, lewati checklist SEO di `CLAUDE.md` Bagian 5 (judul ≤60 karakter,
1–3 internal link, alt text, satu H1, tanpa keyword stuffing).

## Pengembangan lokal

```bash
hugo server -D          # pratinjau di http://localhost:1313 (termasuk draft)
npm install             # sekali saja — hanya untuk test
npm test                # Vitest: tests/share.test.js & tests/analytics.test.js
```

⚠️ **Node/npm dev-only.** Build produksi murni Hugo dan tidak menyentuh `package.json`
maupun `node_modules/`. Menambah devDependency tidak membebani pengunjung.

## Otomasi (GitHub Actions)

| Workflow | Pemicu | Fungsi |
|---|---|---|
| `hugo.yml` | push `main` | build + deploy ke GitHub Pages |
| `auto-draft.yml` | cron harian 08:17 WIB (+cadangan 08:37 & 08:57), atau manual | draf artikel AI (Gemini + foto Pexels/Pixabay) → **PR berlabel `ai-draft`** |
| `manual-draft.yml` | dipicu POS (Pusat Konten) via API | form "Tulis Manual" + gambar Supabase → PR |
| `add-images.yml` | manual | tambah/ganti foto artikel lama tanpa mengubah teks/slug → PR |
| `notify-new-post.yml` | push `main` menyentuh `content/**` | push notification OneSignal + ping **IndexNow** (Bing/Yandex) |
| `post-instagram.yml` | push `main` menyentuh `content/**` | **pratinjau** caption + foto IG/FB (`preview-<slug>.json`); tayang hanya lewat `workflow_dispatch` + `posting: true` |
| `backup.yml` | tiap tanggal 1, 09:00 WIB | arsip ZIP seluruh repo sebagai artifact |

**Draf ditinjau & disetujui di POS "Pusat Konten":**
**https://app.centralcats.id/technology-system** — bukan di halaman PR GitHub. Halaman itu
juga tempat memicu **Buat Artikel** (AI) dan **Tulis Manual**.

**Medsos juga bergerbang tinjau.** Push ke `main` hanya *menyiapkan* caption + foto IG/FB
sebagai `preview-<slug>.json` di release `ig-images`; tidak ada yang tayang sampai ada
`workflow_dispatch` dengan `posting: true`. Alasannya: caption IG tidak bisa diedit lewat
API setelah tayang. Panel Media Sosial di POS masih "Segera Hadir" — sementara ini
tayangkan manual dari tab Actions setelah membaca pratinjaunya.

Deteksi "artikel baru" memakai `git diff --diff-filter=A` — hanya file yang **ditambahkan**,
bukan editan. Semua otomasi non-blocking: gagal ping/post tidak menggagalkan deploy.

**Kriteria blog vs medsos sengaja beda:** blog memuat semua hewan, medsos (IG/FB) hanya
kucing & anjing. Detail di `CLAUDE.md` Bagian 8 & 13.

**GitHub Secrets:** `GEMINI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`,
`ONESIGNAL_REST_API_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`, `RESEND_API_KEY`.
Jangan pernah menaruhnya di kode/commit.

## Integrasi keluar

- **`/index.json`** → feed "Artikel Terbaru" yang ditarik situs utama `centralcats.id`.
  **Dibatasi 20 artikel — jangan diubah.**
- **`/search-index.json`** → indeks pencarian (SEMUA artikel), untuk kotak cari di header
  dan halaman `/cari/`. Terpisah dari `index.json`.
- **`/sitemap.xml`** → otomatis dari Hugo, sudah disubmit ke Search Console & Bing.
  Tidak perlu submit ulang tiap artikel baru.
- **GA4 `G-SGYPJC015Y`** → satu Measurement ID bersama situs utama, supaya sesi lintas
  subdomain tidak putus.

## Jangan dihapus

`static/CNAME` · `static/google4120ad7b9c49fdb9.html` (Search Console) ·
`static/BingSiteAuth.xml` · `static/f4efa60d1fc581fb45be07ed3edb7d94.txt` (IndexNow) ·
`static/OneSignalSDKWorker.js` · `layouts/index.json` · release GitHub bertag `ig-images` ·
blok SEO & gtag di `<head>` `layouts/_default/baseof.html`.

Alasannya dan daftar lengkapnya ada di `CLAUDE.md` Bagian 6.
