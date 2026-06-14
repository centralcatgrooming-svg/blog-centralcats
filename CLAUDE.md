# CLAUDE.md — Panduan Blog Central Cat's

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

### Tingkat situs (sudah/perlu diatur)
- `enableRobotsTXT = true` sudah aktif → `robots.txt` otomatis.
- Hugo otomatis membuat `sitemap.xml`. **Daftarkan ke Google Search Console** dan submit sitemap.
- Pastikan `baseURL` benar (`https://blog.centralcats.id/`) agar URL kanonik tepat.
- **Disarankan ditambahkan ke template** (`baseof.html`) — minta bantuan untuk implementasi:
  - Tag Open Graph & Twitter Card (judul, deskripsi, gambar) untuk tampilan saat dibagikan.
  - Structured data **JSON-LD `Article`** (judul, penulis, tanggal, gambar) untuk rich result.
  - Tag `<link rel="canonical">`.
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
  - `layouts/index.json` & blok `[outputs] home = ["HTML", "RSS", "JSON"]` di `hugo.toml`
    → ini sumber feed ke situs utama. Rusak = artikel hilang dari `centralcats.id`.
  - `static/CNAME` → berisi `blog.centralcats.id`. Hapus = domain custom mati.
  - `.github/workflows/hugo.yml` → ini yang mem-build & deploy. Rusak = situs tidak ter-update.
  - `baseURL` di `hugo.toml`.
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
