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
   summary = "Ringkasan 1–2 kalimat. Ini juga dipakai sebagai meta description SEO (maks ~155 karakter)."
   images = ["/images/nama-gambar.webp"]   # gambar unggulan, opsional tapi sangat disarankan
   author = "Team Central Cat's"           # opsional; default "Team Central Cat's" bila dikosongkan
   +++
   ```
4. **Kategori utama** = folder. **Subkategori** = field `categories`.
5. Commit & push → tayang otomatis di blog dan di `centralcats.id`.

---

## 4. Aturan Performa (Wajib — Jaga Blog Tetap Cepat)

Kecepatan = pengalaman pengguna + ranking SEO. Patuhi ini:

- **Gambar:** gunakan format **WebP** (atau JPG terkompres). Kompres sebelum upload.
  Lebar maksimal wajar (mis. ≤1600px). Selalu sertakan dimensi bila memungkinkan.
- **Lazy loading:** gambar di luar layar harus `loading="lazy"` (kartu sudah menerapkan ini).
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
- ✅ `baseURL` sudah benar (`https://blog.centralcats.id/`) → URL kanonik tepat.
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
  - `baseURL` di `hugo.toml`.
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
  cron `17 1 * * 1-6` = **Senin–Sabtu 08:17 WIB** (01:17 UTC). **Minggu libur.**
  (Menit ganjil `:17` dipilih agar tak bentrok beban puncak GitHub di menit `:00`.)
  Bisa juga dijalankan manual dari tab Actions (input `jumlah` & `kategori`).
- **Kategori mengikuti hari** (zona WIB), dipilih otomatis oleh `scripts/generate_drafts.py`
  (env `SECTION="auto"`/kosong), atau dipaksa lewat input `kategori` saat run manual:
  - Senin & Kamis → **Kesehatan Hewan**
  - Selasa & Jumat → **Panduan & Tips**
  - Rabu → **Bisnis Hewan**
  - Sabtu → **Berita & Tren**
- **Gambar (kondisional):** kategori **Berita & Tren** = **foto asli (Pexels)** (fallback ke
  ilustrasi Pixabay bila kosong). Kategori **non-berita** = **dicampur acak** antara
  **foto (Pexels)** & **ilustrasi/kartun (Pixabay)** dengan **saling fallback**, supaya gambar
  bervariasi (kadang foto, kadang kartun) tapi tetap relevan. Kata kunci gambar dibuat
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
- **Output:** Pull Request berlabel `ai-draft`, **branch unik per run** → tinjau → Merge = terbit.
- **GitHub Secrets yang dipakai:** `GEMINI_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY`.
- **Belum terpasang:** RSS berita real-time untuk **Berita & Tren** (Sabtu). Sementara artikel
  Sabtu memakai pengetahuan Gemini + foto Pexels (bukan berita real-time). Akan disambungkan
  saat URL portal RSS tersedia.

---

## 9. Pencarian Artikel

- Halaman **`/cari/`** (`content/cari.md` + layout `layouts/_default/search.html`).
  Pencarian **client-side** (filter judul/ringkasan/kategori di browser), **nol library**
  (patuh Aturan Performa). Menu **"Cari"** ada di navigasi utama.
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
