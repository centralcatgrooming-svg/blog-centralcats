# CLAUDE.md — Panduan Blog Central Cat's

> Cetak biru desain & roadmap: baca `.ai/ROADMAP.md` sebelum mengerjakan tugas UI/fitur.

> File ini adalah instruksi tetap untuk Claude Code (dan kontributor) saat bekerja di
> repo `blog-centralcats`. Letakkan di **root repo**. File ini TIDAK dipublikasikan
> oleh Hugo (Hugo hanya memproses folder `content/`), jadi tidak memengaruhi kecepatan situs.
> Baca dan patuhi seluruh isinya sebelum membuat, mengedit, atau menghapus apa pun.

---

## 1. Tentang Proyek

Blog resmi **Central Cat's** — bisnis grooming, petshop, dan cat hotel kucing di
Tangerang (Pasar Kemis & Rajeg). Blog ini adalah bagian dari ekosistem:

- `centralcats.id` — situs utama (statis, di GitHub Pages)
- `blog.centralcats.id` — **blog ini** (Hugo, GitHub Pages)
- `shop.centralcats.id` — toko
- `app.centralcats.id` — booking (Vercel)

**Stack:** Hugo (static site generator) → GitHub Pages → custom domain `blog.centralcats.id`.
Build otomatis lewat GitHub Actions (`.github/workflows/hugo.yml`) setiap `push` ke `main`.

**Judul situs publik:** **"Central Cat's News"** (di `hugo.toml` `title` & `content/_index.md`).
Nama brand di footer & narasumber tetap **"Central Cat's"** (tanpa "News"). Desain bertahap
mengikuti `.ai/ROADMAP.md` (Tahap 0–7 sudah selesai: token+dark mode, tipografi, homepage portal,
halaman artikel, header+pencarian, Indeks Hewan A‑Z, Kisah Sukses, poles aksesibilitas/performa).

**Integrasi penting:** Hugo menghasilkan `index.json` di root situs
(`https://blog.centralcats.id/index.json`). Situs utama `centralcats.id` menarik file ini
untuk menampilkan section "Artikel Terbaru" secara otomatis. **Jangan rusak feed ini.**

---

## 2. Visi & Misi

### Visi
Menjadi rujukan tepercaya nomor satu di Indonesia untuk pemilik hewan peliharaan —
khususnya pecinta kucing — dalam hal perawatan, kesehatan, dan gaya hidup anabul,
sekaligus memperkuat posisi Central Cat's sebagai merek grooming & petshop yang peduli
dan ahli di bidangnya.

### Misi
1. **Mengedukasi** pemilik hewan dengan konten yang akurat, mudah dipahami, dan dapat
   langsung dipraktikkan — bukan sekadar mengejar trafik.
2. **Membangun kepercayaan** lewat informasi kesehatan yang bertanggung jawab dan selalu
   menyarankan konsultasi ke dokter hewan untuk kasus serius.
3. **Menyajikan konten original** yang ditulis dengan sudut pandang dan pengalaman Central Cat's,
   bukan jiplakan dari situs lain.
4. **Menghubungkan** pembaca dengan layanan Central Cat's secara natural dan tidak memaksa.
5. **Mendukung komunitas** pecinta hewan peliharaan di Tangerang dan sekitarnya.

### Nada & gaya menulis
- Hangat, ramah, dan menggunakan istilah akrab seperti "anabul".
- Bahasa Indonesia yang jelas dan tidak kaku; hindari jargon berlebihan.
- Faktual dan jujur; tidak melebih-lebihkan.
- Selalu mengutamakan kesejahteraan hewan.

---

## 3. Cara Menulis Artikel Baru

1. Pilih folder kategori yang sesuai di `content/`:
   `berita-tren/`, `kesehatan-hewan/`, `bisnis-hewan/`, atau `panduan-tips/`.
2. Buat file `nama-artikel-deskriptif.md` (slug pakai huruf kecil & tanda hubung).
3. Front matter standar:
   ```
   +++
   title = "Judul Artikel yang Jelas dan Menarik"
   date = 2026-06-14T09:00:00+07:00
   categories = ["Kesehatan Kucing"]   # = SUBKATEGORI
   tags = ["kucing", "kesehatan", "bulu"]
   hewan = ["kucing"]                       # taxonomy Indeks Hewan A-Z (huruf kecil; default ["kucing"])
   summary = "Ringkasan 1–2 kalimat. Ini juga dipakai sebagai meta description SEO (maks ~155 karakter)."
   images = ["/images/nama-gambar.webp"]   # gambar unggulan, opsional tapi sangat disarankan
   author = "Team Central Cat's"           # opsional; default "Team Central Cat's" bila dikosongkan
   +++
   ```
4. **Kategori utama** = folder. **Subkategori** = field `categories`. **`hewan`** = taxonomy untuk
   halaman **Indeks Hewan A-Z** (`/hewan/`); isi huruf kecil (mis. `["kucing"]`, `["anjing"]`).
5. Commit & push → tayang otomatis di blog dan di `centralcats.id`.

---

## 4. Aturan Performa (Wajib — Jaga Blog Tetap Cepat)

Kecepatan = pengalaman pengguna + ranking SEO. Patuhi ini:

- **Gambar:** gunakan format **WebP** (atau JPG terkompres). Kompres sebelum upload.
  Lebar maksimal wajar (mis. ≤1600px). Selalu sertakan dimensi bila memungkinkan.
  Gambar auto-draft sudah dikonversi WebP q80 ≤1200px oleh `generate_drafts.py`.
- **Lazy loading & LCP (Tahap 7 lanjutan):** SEMUA `<img>` konten punya `loading="lazy"`
  KECUALI elemen **LCP** yang justru `loading="eager" fetchpriority="high"`:
  **featured #1 di homepage** (`index.html`, kartu besar paling atas) & **hero artikel**
  (`single.html`, `img.post-hero`). Kartu grid (`card.html`), scard (`index.html`), dan
  logo footer (`baseof.html`) = `lazy`; logo header tetap eager (di atas layar).
  Ukuran gambar dijamin lewat `aspect-ratio`/`object-fit` di CSS — **jangan tambah**
  `width`/`height` di `<img>` (berisiko bentrok). Belum pakai `srcset` responsif (opsional).
- **Jangan tambah library JavaScript berat** (jQuery, framework, slider besar, dll) tanpa
  alasan kuat. Blog ini sengaja ringan dengan CSS inline + JS minimal.
- **Jangan tambah banyak font eksternal.** Saat ini pakai system font (cepat, nol request).
  Maksimal 1 font kustom bila benar-benar perlu, dan harus di-`preload` + `font-display: swap`.
- **Jangan embed iframe berat** (video autoplay, widget pihak ketiga) di banyak tempat.
- Build produksi sudah memakai `--gc --minify`. Jangan matikan minify.
- Hindari CSS/JS yang tidak terpakai menumpuk di `baseof.html`.

Target: skor Lighthouse Performance ≥ 90 di mobile.

---

## 5. Aturan SEO (Maksimalkan Peluang Ranking)

> ⚠️ **Realistis:** tidak ada yang bisa menjamin "page one Google". Ranking bergantung pada
> persaingan kata kunci, backlink, otoritas domain, dan konsistensi publikasi dari waktu ke waktu.
> Aturan di bawah memaksimalkan peluang, tetapi hasilnya butuh waktu dan konsistensi.

### Per artikel (checklist wajib)
- [ ] **Judul (`title`):** mengandung kata kunci utama, jelas, menarik, idealnya ≤ 60 karakter.
- [ ] **Meta description (`summary`):** 1–2 kalimat memikat, ≤ ~155 karakter, mengandung kata kunci.
- [ ] **Slug** (nama file): pendek, deskriptif, pakai kata kunci, huruf kecil & tanda hubung.
- [ ] **Satu H1 per halaman** (judul sudah jadi H1 otomatis). Isi artikel pakai **H2/H3** berurutan.
- [ ] **Kata kunci** muncul natural di paragraf pembuka, satu subjudul, dan kesimpulan —
      **tanpa keyword stuffing**.
- [ ] **Gambar unggulan** (`images`) + semua gambar punya **alt text** deskriptif.
- [ ] **Internal link:** tautkan ke 1–3 artikel lain yang relevan di blog ini.
- [ ] **Tautan ke layanan** Central Cat's bila relevan (mis. ajakan grooming/booking) secukupnya.
- [ ] Panjang artikel cukup untuk membahas topik tuntas (umumnya 600–1500+ kata untuk topik kompetitif).
- [ ] Tulis untuk **manusia dulu**, mesin pencari kedua. Konten harus benar-benar bermanfaat.

### Tingkat situs (status terkini)
- ✅ `enableRobotsTXT = false` → `robots.txt` & `llms.txt` kini disajikan dari **file statis**
  (`static/robots.txt` + `static/llms.txt`, izinkan crawler mesin pencari & AI + Sitemap).
  **Jangan aktifkan kembali** `enableRobotsTXT` tanpa paham dampaknya — Hugo akan menimpa file statis itu.
- ✅ `baseURL` = `https://blog.centralcats.id/` (https) → URL kanonik tepat. Workflow `hugo.yml`
  mem-build dengan `--baseURL "https://blog.centralcats.id/"` (**hardcoded https**); JANGAN kembalikan
  ke `${{ steps.pages.outputs.base_url }}` karena bisa menghasilkan `http://` → canonical salah di GSC.
- ✅ **Judul SEO homepage terpisah dari teks tampilan:** `content/_index.md` punya `seo_title`
  (dipakai `<title>` + OG/Twitter title saat `.IsHome`) & `description` (meta/OG/Twitter desc home).
  Teks di bawah "Artikel Terbaru" tetap dari `.Site.Params.description` (`hugo.toml [params]`).
- ✅ **Aksesibilitas & performa (Tahap 7):** semua `<img>` punya `alt` = judul artikel; SVG dekoratif
  `aria-hidden`; font Google dimuat non-blocking (`rel=preload`→`stylesheet` + `<noscript>`); indikator
  fokus keyboard `:focus-visible` (putih di header, brand di body).
- ✅ **Google Search Console** sudah terverifikasi (file `static/google4120ad7b9c49fdb9.html`
  — **jangan dihapus**, Google mengecek ulang sewaktu-waktu).
- ✅ `sitemap.xml` (otomatis dari Hugo) sudah **disubmit** ke Search Console.
- ✅ **Sudah terpasang di template** (`baseof.html`, di dalam `<head>`):
  - Tag **Open Graph & Twitter Card** (judul, deskripsi, gambar) untuk tampilan saat dibagikan.
  - Structured data **JSON-LD `Article`** (judul, tanggal, gambar, **penulis**, publisher) — hanya di
    halaman artikel. Field `author` diambil dari `.Params.author`, default **"Team Central Cat's"**.
  - Tag `<link rel="canonical">`.
  - Variabel bersama `$title`/`$desc`/`$img`: `$desc` ambil dari `description` → `summary` → deskripsi situs;
    `$img` ambil `images[0]` (di-`absURL`), fallback `/logo.png`. **Jangan ubah tanpa paham dampaknya.**
- Konsistensi publikasi (mis. 1–3 artikel berkualitas per minggu) lebih penting daripada volume sekali banyak.

### E-E-A-T (penting untuk konten kesehatan)
- Tunjukkan keahlian: sebutkan pengalaman Central Cat's, sertakan nama penulis bila ada.
- Untuk klaim medis/kesehatan, rujuk sumber tepercaya dan sarankan konsultasi dokter hewan.
- Akurasi membangun otoritas; satu artikel salah bisa merusak kepercayaan & ranking.

---

## 6. LARANGAN (Tidak Boleh Dilanggar)

### Konten & hak cipta
- ❌ **Dilarang menyalin/menjiplak** artikel, paragraf, atau struktur dari situs lain.
  Tulis ulang sepenuhnya dengan kata sendiri. Ambil **fakta**-nya, lalu sebutkan sumber.
- ❌ **Dilarang memakai gambar berhak cipta** tanpa lisensi. Gunakan foto milik Central Cat's
  sendiri, atau stok gratis berlisensi (mis. Unsplash, Pexels) dengan atribusi bila diminta.
- ❌ **Dilarang mempublikasikan konten hasil AI mentah tanpa ditinjau manusia.** Semua draf
  (termasuk dari AI) wajib dibaca, diperiksa akurasinya, dan disetujui sebelum tayang.

### Kesehatan hewan (sangat penting)
- ❌ **Dilarang memberi dosis obat spesifik, diagnosis pasti, atau "resep" medis** seolah-olah
  pengganti dokter hewan. Topik kesehatan harus bersifat edukasi umum.
- ❌ **Dilarang menyebarkan informasi kesehatan yang belum terverifikasi** atau berpotensi
  membahayakan hewan. Bila ragu, jangan publikasikan.
- ✅ Untuk gejala/penyakit/pertolongan pertama, **selalu sarankan konsultasi ke dokter hewan**.

### SEO & integritas
- ❌ **Dilarang keyword stuffing**, teks tersembunyi, cloaking, atau teknik black-hat lain
  (berisiko penalti Google).
- ❌ **Dilarang membeli/menukar backlink spam** atau ikut skema link manipulatif.
- ❌ **Dilarang membuat judul clickbait yang menyesatkan** isi artikel.

### Privasi & etika
- ❌ **Dilarang menampilkan data pribadi pelanggan** (nama lengkap, alamat, kontak, foto)
  tanpa izin.
- ❌ **Dilarang membuat klaim berlebihan/menyesatkan** soal layanan atau hasil perawatan.

### Teknis (jangan dirusak)
- ❌ **Jangan ubah/hapus tanpa paham dampaknya:**
  - `layouts/index.json` & blok `[outputs] home` di `hugo.toml`
    (kini `["HTML", "RSS", "JSON", "SearchIndex"]`) → `JSON` = sumber feed ke situs utama
    (jangan hapus/ubah, & tetap dibatasi 20 artikel); `SearchIndex` = indeks pencarian
    (lihat Bagian 9). Rusak = artikel hilang dari `centralcats.id`.
  - `static/CNAME` → berisi `blog.centralcats.id`. Hapus = domain custom mati.
  - `static/google4120ad7b9c49fdb9.html` → file verifikasi Google Search Console. Hapus = verifikasi bisa lepas.
  - `.github/workflows/hugo.yml` → ini yang mem-build & deploy. Rusak = situs tidak ter-update.
    Argumen `--baseURL "https://blog.centralcats.id/"` harus tetap **https** (lihat Bagian 5).
  - `baseURL` di `hugo.toml` (https).
  - `[taxonomies]` di `hugo.toml` (`category`, `tag`, `hewan`) + template `layouts/hewan/list.html`
    (indeks A-Z) & `layouts/hewan/term.html` (per-hewan). Menghapus salah satu taxonomy bawaan
    (`category`/`tag`) saat menambah kustom = pill/kartu kategori rusak.
  - Blok SEO di `<head>` `baseof.html` (Open Graph, Twitter Card, canonical, JSON-LD Article).
- ❌ Jangan menambah dependensi/library berat yang melanggar Aturan Performa (Bagian 4).
- ✅ Saat menyentuh file teknis inti, tampilkan dulu perubahannya (diff) untuk ditinjau
  sebelum commit & push.

---

## 7. Alur Kerja Standar untuk Claude Code

1. Pahami permintaan dan cocokkan dengan aturan di file ini.
2. Untuk artikel baru: ikuti Bagian 3 + checklist SEO Bagian 5.
3. Untuk perubahan teknis: ikuti larangan Bagian 6 dan **tampilkan diff sebelum push**.
4. Commit dengan pesan yang jelas dalam bahasa Indonesia.
5. Push ke `origin main`. Build otomatis akan jalan; ingatkan pengguna untuk cek tab Actions
   bila perubahan besar.
6. Git identity: name `centralcatgrooming`, email `centralcatgrooming@gmail.com`.

---

## 8. Sistem Auto-Draft Artikel (AI) — v3

Pipeline pembuat draf artikel otomatis. **Output selalu berupa Pull Request** untuk ditinjau
manusia sebelum tayang (lihat larangan "AI mentah" Bagian 6) — Merge = terbit, Close = buang.

- **Jadwal otomatis** (GitHub Actions, `.github/workflows/auto-draft.yml`):
  **3 cron** Senin–Sabtu = `17 1 * * 1-6` (**08:17 WIB**) + cadangan `37 1 * * 1-6`
  (**08:37**) & `57 1 * * 1-6` (**08:57**). **Minggu libur.** (Menit ganjil agar tak
  bentrok beban puncak GitHub di menit `:00`.) Cron cadangan ada karena scheduler GitHub
  kadang **menunda/melewati** cron saat beban tinggi.
  Bisa juga dijalankan manual dari tab Actions (input `jumlah` & `kategori`).
- **Guard anti-dobel (maks 1 artikel/hari):** langkah "Guard anti-dobel" di workflow aktif
  **HANYA saat `event_name == 'schedule'`**. Ia cek via GitHub Search apakah sudah ada PR
  berlabel `ai-draft` yang **dibuat hari ini** (UTC); bila ada → langkah Generate & buka-PR
  **dilewati dengan sukses** (job hijau, pakai `::notice::`, tanpa email gagal). Jadi dari 3
  cron, hanya yang pertama membuat artikel. **Trigger manual (`workflow_dispatch`) BEBAS guard**
  → tetap bisa memaksa buat artikel kapan saja untuk tes. Jangan ubah `generate_drafts.py`
  untuk dedup ini — guard murni di level workflow.
- **Kategori mengikuti hari** (zona WIB), dipilih otomatis oleh `scripts/generate_drafts.py`
  (env `SECTION="auto"`/kosong), atau dipaksa lewat input `kategori` saat run manual:
  - Senin & Kamis → **Kesehatan Hewan**
  - Selasa & Jumat → **Panduan & Tips**
  - Rabu → **Bisnis Hewan**
  - Sabtu → **Berita & Tren**
- **Gambar (foto-first):** **SEMUA kategori** mengutamakan **foto asli (Pexels)** agar tampilan
  profesional & konsisten. **Ilustrasi/kartun (Pixabay)** hanya dipakai sebagai **cadangan terakhir**
  bila Pexels tidak punya hasil untuk query tsb (supaya artikel tetap punya gambar). Kata kunci gambar dibuat
  **konkret/visual** dan **mengikuti HEWAN/SUBJEK artikel** (mis. kucing, anjing, kelinci,
  ayam) — **tidak dipaksa selalu kucing**. Semua dikonversi **WebP ≤1200px**
  (patuh Aturan Performa Bagian 4).
- **Cakupan hewan:** **kucing adalah TEMA UTAMA** blog (mayoritas artikel), tetapi artikel
  **boleh** membahas **hewan peliharaan lain** (anjing, kelinci, hamster, burung, ikan, dll)
  bila relevan & bermanfaat — **tidak harus selalu kucing**. Untuk **Bisnis Hewan**, cakupan
  meluas ke **ternak halal** (lihat aturan HALAL). Isi & gambar menyesuaikan hewan yang dibahas.
- **Aturan HALAL** (khusus kategori Bisnis Hewan): boleh hewan peliharaan & ternak **halal**
  (ayam, bebek, kambing, sapi, domba, kelinci, ikan, dll); **DILARANG** hewan haram (babi/celeng)
  demi menghormati keyakinan muslim.
- **FAQ & gaya:** tiap artikel memuat blok `[[faq]]` di front matter (3–5 tanya-jawab) dan
  ditulis **answer-first** (paragraf pembuka langsung menjawab inti) — baik untuk SEO & asisten AI.
- **Penulis (byline):** tiap draf otomatis menambahkan `author = "Team Central Cat's"` di front matter
  (lihat Bagian 10). Bila perlu, ganti manual ke nama penulis spesifik sebelum merge.
- **Taxonomy `hewan`:** Gemini menentukan hewan utama artikel; ditulis `hewan = [...]` (huruf kecil,
  default `["kucing"]`, hewan haram babi/celeng difilter) → mengisi Indeks Hewan A-Z otomatis.
- **Output:** Pull Request berlabel `ai-draft`, **branch unik per run** → tinjau → Merge = terbit.
- **GitHub Secrets yang dipakai:** `GEMINI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`.
- **Belum terpasang:** RSS berita real-time untuk **Berita & Tren** (Sabtu). Sementara artikel
  Sabtu memakai pengetahuan Gemini + foto Pexels (bukan berita real-time). Akan disambungkan
  saat URL portal RSS tersedia.

### 8a. RENCANA: gambar pindah ke Cloudflare R2 (DITUNDA — belum urgent)

> **Status 29 Jun 2026: DICOBA lalu DIBATALKAN (gambar tetap di GitHub Pages).** Implementasi R2
> sempat dikerjakan penuh (rewire skrip + template + 5 GitHub Secrets + bucket `blog-centralcats-images`
> aktif), TAPI saat diuji ketahuan **ISP Indonesia (terbukti di XL Axiata) MEMBLOKIR domain `*.r2.dev`
> di level DNS** → `pub-….r2.dev` di-resolve ke `blockpage.xlaxiata.id`. Artinya URL publik `r2.dev`
> **TIDAK BISA dipakai** host gambar untuk pengunjung Indonesia (gambar artikel gagal tampil).
> Endpoint upload `…r2.cloudflarestorage.com` TIDAK diblokir (upload jalan) — yang mati hanya read publik.
> **Keputusan: semua perubahan R2 di-revert, gambar baru tetap `static/images/` → GitHub Pages.**
>
> ⚠️ **JANGAN ulang jalur `r2.dev`.** Kalau R2 dikerjakan lagi nanti, **WAJIB pakai custom domain di
> Cloudflare** (mis. `img.centralcats.id`) — yang TIDAK diblokir. Itu mensyaratkan **zona DNS ada di
> Cloudflare**: entah pindahkan zona `centralcats.id` dari Hostinger ke Cloudflare (migrasi penuh,
> hati-hati record email/MX), atau pakai **domain terpisah** khusus CDN yang ditaruh di Cloudflare
> (`centralcats.id` tetap utuh di Hostinger). Rencana ini dikaitkan ke rencana pakai Cloudflare untuk
> proyek **shop** ke depan.
>
> Belum urgent juga: repo ~3 MB, `static/images/` baru **~32 file `.webp` (~1,8 MB)**, jauh dari limit
> GitHub Pages (1 GB site / 100 GB-bln bandwidth). Kerjakan saat ada custom domain Cloudflare siap
> **ATAU** trigger nyata (repo membengkak / butuh banyak gambar).

**Kondisi sekarang:** gambar `.webp` **di-commit ke git** di `static/images/` lalu di-serve GitHub
Pages. Tiap artikel = +1 gambar di **history git selamanya** (biner di git tak pernah menyusut) →
bloat jangka panjang + build `hugo.yml` (`fetch-depth: 0`) melambat seiring waktu.

**Rencana:** offload gambar ke **Cloudflare R2** (object storage S3-compatible, **egress gratis**,
free tier 10 GB) → repo tetap ramping (cuma markdown + template), gambar di-serve via CDN /
`img.centralcats.id`. **Target = R2, BUKAN Supabase Storage** (jangan bebani DB POS yang dijaga ringan).

**Titik rewire saat dikerjakan:**
1. `scripts/generate_drafts.py` + `scripts/add_images.py` → setelah konversi WebP, **upload ke R2**
   (boto3/S3-compat) + tulis **URL R2 penuh** di front-matter `images = [...]` (bukan simpan ke `static/images/`).
2. Template Hugo yang baca `images[0]` (lihat Bagian 5: `$img` di-`absURL`; JSON-LD `Article` + Open Graph)
   → **deteksi URL absolut**: kalau `images[0]` diawali `http` → pakai apa adanya (JANGAN `absURL`); path
   lokal lama → perilaku sekarang. (Pola backward-compat sama spt `assetUrl()` di repo POS.)
3. `.gitignore` → tambah `/static/images/` (stop commit gambar baru).
4. Migrasi **30 gambar lama** → upload ke R2 + rewrite `images = [...]` di artikel terkait (one-off).
5. GitHub Secrets baru: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_BUCKET` (`blog-centralcats-images`), `R2_PUBLIC_URL`.

**Catatan:** project **Cloudflare Pages** (dibuat 28 Jun) = **HOSTING, BUKAN ini** — tak meng-offload
gambar. Biarkan tak tersambung ke domain (blog tetap di GitHub Pages) sampai diputuskan terpisah.

---

## 9. Pencarian Artikel

- Halaman **`/cari/`** (`content/cari.md` + layout `layouts/_default/search.html`).
  Pencarian **client-side** (filter judul/ringkasan/kategori di browser), **nol library**
  (patuh Aturan Performa). Tetap ada sebagai halaman hasil lengkap/cadangan.
- **Kotak cari di header** (`baseof.html`) dengan **dropdown hasil live** dari `/search-index.json`
  (maks 6, Enter → `/cari/?q=`): desktop = `#cc-hsearch` di topbar; mobile = ikon kaca `#cc-msearch-btn`
  membuka baris cari `#cc-msearch`. Index di-`fetch` **sekali** & dibagi kedua kotak (JS `init(...)`
  bersama). Link menu "Cari" disembunyikan (digantikan kotak/ikon ini).
- **Indeks:** `layouts/index.searchindex.json` menghasilkan **`/search-index.json`**
  (berisi **SEMUA artikel**), lewat output format `[outputFormats.SearchIndex]` di `hugo.toml`.
- ⚠️ **PENTING:** `index.json` (feed ke situs utama `centralcats.id`) **tetap dibatasi 20 artikel
  — JANGAN diubah.** Pencarian memakai `search-index.json` yang **terpisah & lengkap**, bukan
  `index.json`.

---

## 10. Tampilan & Komponen

- **FAQ accordion** — gaya untuk class `cc-faq`, `cc-faq__item`, `cc-faq__q`, `cc-faq__a`
  ada di blok `<style>` pada `layouts/_default/baseof.html`. Markup FAQ ada di
  `layouts/_default/single.html` (render hanya bila artikel punya `[[faq]]`) + JSON-LD `FAQPage`.
- **Byline penulis** — di `layouts/_default/single.html`, dekat tanggal artikel ditampilkan
  `Ditulis oleh {{ .Params.author | default "Team Central Cat's" }}`. Default ini juga dipakai
  di JSON-LD `Article` (`baseof.html`) — jadi artikel tanpa field `author` tetap punya penulis.

> Semua CSS komponen ada di blok `<style>` `baseof.html` dan **memakai token warna** (`var(--…)`)
> agar otomatis ikut **dark mode** (`data-theme`, toggle `#cc-theme-toggle` desktop + `#cc-theme-toggle-m`
> di drawer mobile, simpan ke `localStorage`). Jangan hardcode warna; pakai token. Font: heading
> **Fraunces** (serif), body **Inter** (sans).

- **Homepage portal** (`layouts/index.html`): hanya artikel ber-`Section` (terbaru dulu). **Featured grid**
  (`.feat-grid`: 1 kartu besar + 2 kecil), **strip "Terkini"** (running text/ticker `.ticker`),
  **seksi per kategori** (`.cat-sec`, 3 artikel + "Lihat semua"). Kartu sisa pakai `partial card.html`.
- **Tag warna per kategori** (berdasar `.Section`): `.badge--<section>` (kartu) & `.pill-light--<section>`
  (featured) — token `--cat-health/guide/biz/news-*`. Slug: `kesehatan-hewan`, `panduan-tips`,
  `bisnis-hewan`, `berita-tren`.
- **Placeholder kartu tanpa gambar** — `.cc-noimg` + ikon kucing SVG (kartu grid latar `--brand-soft`;
  featured latar gelap `#1a2744`). Dipakai di `card.html` & featured `index.html`.
- **Halaman artikel** (`single.html`): header `.post-head` (pill kategori → H1 serif → `.post-meta`
  penulis · tanggal · `{{ .ReadingTime }} menit baca`), **hero** `.post-hero` (16/8, hanya bila ada
  `images`), blockquote bergaya.
- **Indeks Hewan A-Z** — `layouts/hewan/list.html` (`/hewan/`, chip `.hewan-chip` dikelompok A-Z, ada
  fallback "Indeks sedang dilengkapi" bila kosong) & `layouts/hewan/term.html` (`/hewan/<nama>/`). Link
  di nav header & footer.
- **Kisah Sukses** — artikel `tipe = "kisah-sukses"` menampilkan **kartu narasumber** `.cc-narsum`
  (nama + tombol LINK ke `instagram`/`youtube`/`tiktok`/`situs`, **bukan embed**) di atas konten.
  Front matter: `tipe`, `narasumber`, dan URL sosial/situs opsional. Artikel biasa tidak terpengaruh.

---

## 11. Notifikasi Push "Berita Terbaru" (OneSignal Web Push)

Pengunjung bisa berlangganan **notifikasi push browser** dan otomatis dapat pemberitahuan
tiap artikel baru terbit. Situs statis (tanpa backend), jadi pakai **OneSignal** (gratis) +
**GitHub Actions** untuk pengiriman.

- **App ID (publik):** `844d69d1-7c8c-4fca-a45d-9f6cccd1a6b6` (boleh ada di kode klien).
- **Opt-in / SDK (Phase 1):** init SDK OneSignal **v16** di `<head>` `baseof.html`
  (`OneSignalSDK.page.js`, di-`defer` agar tak ganggu performa) + **service worker**
  `static/OneSignalSDKWorker.js` (tersaji di `/OneSignalSDKWorker.js`, content-type
  `application/javascript`). Prompt langganan ("Slide Prompt") diatur di **dashboard OneSignal**,
  bukan di kode.
- **Auto-send (Phase 2):** workflow `.github/workflows/notify-new-post.yml` ter-trigger saat
  **push ke `main`** menyentuh `content/**`. Ia mendeteksi file artikel **BARU** (git diff
  `--diff-filter=A`, hanya yang DITAMBAHKAN — bukan editan) lalu menjalankan
  `scripts/notify_new_post.py` yang memanggil **OneSignal REST API**
  (`POST https://api.onesignal.com/notifications`, header `Authorization: Key …`,
  segment `"Subscribed Users"`, field `headings`/`contents`/`url`/`chrome_web_image`).
  Skrip pakai **pustaka standar** (tanpa pip install) & aman bila belum ada subscriber.
- **Secret:** `ONESIGNAL_REST_API_KEY` (GitHub Secret, dari OneSignal "API/REST key" —
  istilah baru "API Authentication Key"). **JANGAN** taruh di kode/commit.
- **Catatan iOS:** push web hanya jalan bila situs di-"Add to Home Screen" (PWA) — batasan Apple.
  Android Chrome & desktop mulus.
- ❌ **Jangan hapus/ubah tanpa paham:** `static/OneSignalSDKWorker.js`, blok init OneSignal di
  `baseof.html`, `scripts/notify_new_post.py`, `.github/workflows/notify-new-post.yml`.
- **Status:** pipeline auto-send terbukti jalan (deteksi artikel baru → REST API balas `200`).
  **Belum** dikonfirmasi terkirim ke device karena uji pertama 0 subscriber (kebetulan
  subscribe via incognito — tidak persisten). Uji ulang: subscribe di **jendela normal**,
  verifikasi 1 "Subscribed" di dashboard, lalu terbitkan/kirim ulang.
