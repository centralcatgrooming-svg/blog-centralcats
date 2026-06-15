# ROADMAP — Central Cat's News (Premium Knowledge Platform)

Dokumen ini = cetak biru & patokan. Dibaca dulu sebelum mengerjakan tugas UI/fitur apa pun.
Prinsip: **tetap Hugo statis + GitHub Pages, ringan, JS minimal.** Jangan ganti framework. Jangan rusak yang sudah jalan.

---

## 1. Visi
Blog jadi "mesin konten SEO" yang terlihat **premium** (rasa editorial seperti Medium/NYT/Vercel) tapi **terstruktur seperti portal/majalah** — banyak fitur, tetap tertata, ringan, dan direkomendasikan mesin pencari + asisten AI (SEO/GEO/E-E-A-T). Kucing tema utama, tapi mencakup hewan peliharaan lain & ternak halal.

## 2. Identitas Desain (patokan visual)
- **Warna brand:** biru `#1e3a8a` (brand-dark `#162d6b`), aksen merah logo `#e23b3b`.
- **Sistem warna pakai CSS variabel (design token)** — wajib, karena jadi fondasi dark mode & seluruh komponen.
- **Dark mode:** ada **tombol toggle** di header; default ikut preferensi sistem; pilihan disimpan (localStorage). Mode gelap = navy pekat, aksen biru dibuat lebih terang agar kontras.
- **Tipografi:** heading **serif** (mis. Fraunces) yang berkarakter + body **sans** (mis. Inter) yang enak dibaca. Ukuran lega, line-height ~1.7, lebar baca nyaman.
- **Rasa:** bersih, jarak lega, bayangan halus, warna terkendali. BUKAN template WordPress gratisan (hindari nav tebal warna ngejreng, banyak tag warna-warni, slot iklan, baris thumbnail padat).

## 3. Komponen UI
- **Header** (sticky): logo + menu + **kolom pencarian** (bukan link) + tombol dark mode.
- **Pencarian:** kolom di header, hasil muncul **seketika (dropdown)** dari `search-index.json`; halaman `/cari/` tetap sebagai cadangan/hasil lengkap.
- **Featured grid** (homepage): 1 artikel besar (judul overlay di gambar) + beberapa kartu kecil.
- **Strip "Terkini"**: headline terbaru (statis/ringan, bukan slider berat).
- **Tag warna per kategori** (lembut, elegan): Kesehatan=hijau, Panduan=biru, Bisnis=kuning, Berita=merah.
- **Seksi per kategori** di homepage: judul + aksen warna + "Lihat semua →" + 3 kartu.
- **Kartu artikel:** gambar + tag + judul + ringkasan + meta (tanggal · penulis), efek hover halus.
- **Halaman artikel:** lebar baca nyaman, byline "Team Central Cat's", waktu baca, gambar header, FAQ accordion, artikel terkait.

## 4. Fitur Baru
### 4a. Indeks Hewan A-Z (pakai Hugo taxonomy)
- Tambah taxonomy **`hewan`** di front matter tiap artikel (mis. `hewan = ["kucing"]`, `["ayam"]`).
- Hugo otomatis membuat halaman **Indeks Hewan A-Z** + halaman per hewan (`/hewan/kucing/`, dst).
- Auto-draft mengisi `hewan` otomatis (Gemini tahu subjeknya). Artikel lama ditandai sekali (default "kucing").
- Manfaat: navigasi luas tapi tertata + "topic hub" yang kuat untuk SEO.

### 4b. Tipe Konten "Kisah Sukses" (individu, BUKAN profil UMKM)
- Untuk sosok **individu** inspiratif terkait hewan: kreator/influencer hewan, peternak milenial, pemilik berdedikasi, dll.
- Front matter contoh:
  ```
  tipe = "kisah-sukses"
  nama = "..."          # nama individu
  instagram = "..."     # opsional
  youtube = "..."       # opsional
  tiktok = "..."        # opsional
  ```
- Template menampilkan **kartu profil narasumber**: nama + tombol "Ikuti di IG/YouTube/TikTok".
- **Link/tombol, bukan embed video** (jaga performa).
- **Etika & hak cipta:** tulis original + cantumkan sumber; pakai info publik atau seizin yang bersangkutan.
- Manfaat: narasumber nyata = sinyal **E-E-A-T** kuat (dipercaya Google & AI).

## 5. Prinsip Teknis (jangan dilanggar)
- Hugo-native dulu; tambah JavaScript hanya bila perlu.
- **Jaga yang sudah jalan:** auto-draft AI (PR review), SEO (JSON-LD, OG, canonical, sitemap, robots/llms), FAQ schema, pencarian, backup bulanan.
- **`index.json` feed ke situs utama TETAP dibatasi 20 artikel & hanya artikel ber-section — JANGAN diubah.** Pencarian pakai `search-index.json` terpisah.
- Repo situs utama (`centralcats`): branch + PR, jangan push langsung ke main.

## 6. Tahapan Eksekusi (satu per satu, tiap tahap = 1 sesi Claude Code, tampilkan diff dulu)
- **Tahap 0 — Fondasi:** ubah warna jadi CSS variabel (token) + pasang **dark mode toggle**. (Wajib pertama.)
- **Tahap 1 — Tipografi & warna global:** font heading+body, skala, link, jarak.
- **Tahap 2 — Homepage portal:** featured grid + strip Terkini + tag warna + seksi kategori.
- **Tahap 3 — Halaman artikel:** lebar baca, gambar header, waktu baca, poles FAQ/terkait.
- **Tahap 4 — Header & pencarian:** kolom cari + dropdown hasil + nav rapi.
- **Tahap 5 — Indeks Hewan A-Z:** taxonomy `hewan` + halaman indeks + auto-tag di auto-draft.
- **Tahap 6 — Tipe Kisah Sukses:** front matter + kartu profil narasumber + atribusi sumber.
- **Tahap 7 — Poles akhir:** aksesibilitas, performa (Lighthouse), detail.

## 7. Catatan Pemakaian
- Prototipe acuan: `preview-home.html`, `preview-index.html`, `preview-blog.html`.
- Kerjakan bertahap agar hemat token Claude Code & mudah dites (cek build hijau tiap tahap).
- Fitur baru boleh ditambah ke roadmap kapan saja, dikerjakan di gilirannya.
