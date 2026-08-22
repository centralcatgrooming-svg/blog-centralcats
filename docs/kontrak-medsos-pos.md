# Kontrak data: panel "Media Sosial" di POS Pusat Konten

Dokumen ini adalah **kontrak antara repo blog (produsen) dan repo POS (konsumen)**
untuk panel Media Sosial di `https://app.centralcats.id/technology-system`.

Sisi blog **sudah jadi**: tiap artikel baru otomatis menghasilkan pratinjau, dan
tidak ada apa pun yang tayang ke Instagram/Facebook tanpa perintah eksplisit.
Sisi POS **juga sudah LIVE sejak 15 Agu 2026** (commit `481f7f7`) — panel Media
Sosial ada di Pusat Konten, lengkap dengan kunci tombol lolos-refresh dan poll
antrean. Kalimat "Segera Hadir" di versi lama dokumen ini **sudah tidak berlaku**;
jangan lagi menayangkan manual dari tab Actions sebagai jalur normal, karena itu
melewati seluruh pagar yang ada di panel.

Repo blog: `centralcatgrooming-svg/blog-centralcats` (PUBLIC).

---

## 1. Kenapa ada gerbang tinjau

Dulu push ke `main` langsung menayangkan ke IG/FB. Itu berbahaya karena
**caption Instagram TIDAK bisa diedit lewat API setelah tayang** — satu-satunya
koreksi adalah hapus lalu posting ulang manual dari aplikasi IG.

Karena itu tingkat kepulihannya beda jauh dari blog, dan tombolnya **tidak boleh
terlihat sama**:

| | Setujui draf blog | Tayangkan medsos |
|---|---|---|
| Efek | merge PR → artikel terbit | posting ke IG + Halaman FB |
| Membatalkan | hapus/revert artikel | hapus manual di aplikasi IG, caption tak bisa diedit |

---

## 2. Antrean "menunggu tayang"

Sumbernya = **asset release bertag `ig-images`** yang namanya diawali `preview-`.

```
GET https://api.github.com/repos/centralcatgrooming-svg/blog-centralcats/releases/tags/ig-images
→ .assets[] | select(.name | startswith("preview-"))
```

Tiap asset = satu artikel yang menunggu keputusan. Isinya diambil dari
`browser_download_url`, **publik tanpa autentikasi** (repo ini PUBLIC):

```
https://github.com/centralcatgrooming-svg/blog-centralcats/releases/download/ig-images/preview-<slug>.json
```

Antrean ini **membersihkan dirinya sendiri**: begitu sebuah artikel berhasil
tayang, `preview-<slug>.json` dihapus otomatis. Kalau posting GAGAL, pratinjaunya
sengaja dibiarkan supaya bisa dicoba lagi.

⚠️ **Pembersihan itu terjadi di UJUNG workflow, yang berjalan 1–5 menit.** Jadi
sesudah panel mengirim `tayangkan`, kartunya **masih akan terlihat** untuk
beberapa menit. Itu normal — bukan tanda aksinya gagal. Panel WAJIB mengunci
tombol kartu itu selama menunggu; lihat §5.

### Penanda "sudah tayang" — `posted-<slug>.json`

Sesudah IG berhasil, skrip menulis asset `posted-<slug>.json` (media id, post id
FB, jumlah foto, waktu) **sebelum** membuang pratinjaunya. Penanda ini adalah
gerbang anti posting-ganda: selama ia ada, artikel itu **tidak akan** diposting
lagi dan pratinjaunya **tidak akan** dibangkitkan ulang oleh `aksi: "pratinjau"`.

Ini lahir dari kejadian nyata **17 Agu 2026**: satu artikel tayang **dua kali**
di Instagram dan Halaman Facebook hanya karena tombol di panel diklik dua kali
selagi workflow pertama masih berjalan — lalu `aksi: "pratinjau"` menghidupkan
kembali kartunya sehingga bisa tayang untuk ketiga kalinya.

Ingin sengaja memposting ulang? Hapus `posted-<slug>.json` lewat halaman Releases
GitHub — sadar dan manual.

⚠️ Panel **tidak boleh** menampilkan `posted-*.json` sebagai antrean. Saring
tetap dengan awalan `preview-`, bukan sekadar `.json`.

---

## 3. Bentuk `preview-<slug>.json`

```json
{
  "slug": "mengenal-asma-pada-kucing-gejala-dan-penanganan",
  "path": "content/kesehatan-hewan/mengenal-asma-pada-kucing-gejala-dan-penanganan.md",
  "title": "Mengenal Asma pada Kucing: Gejala dan Penanganannya",
  "article_url": "https://blog.centralcats.id/kesehatan-hewan/mengenal-asma-pada-kucing-gejala-dan-penanganan/",
  "image_url": "https://github.com/.../releases/download/ig-images/<slug>.jpg",
  "image_urls": [
    "https://github.com/.../releases/download/ig-images/<slug>.jpg",
    "https://github.com/.../releases/download/ig-images/<slug>-2.jpg",
    "https://github.com/.../releases/download/ig-images/<slug>-3.jpg",
    "https://github.com/.../releases/download/ig-images/<slug>-4.jpg"
  ],
  "carousel": true,
  "photo_credits": ["Foto: Nama Fotografer / Pexels"],
  "hewan": ["kucing"],
  "caption_instagram": "…",
  "caption_facebook": "…"
}
```

| Field | Arti |
|---|---|
| `slug` | identitas artikel; dipakai saat memicu posting |
| `path` | path `.md` di repo; dipakai sebagai input `path` workflow |
| `title` | judul artikel |
| `article_url` | permalink artikel di blog |
| `image_urls` | **JPEG 1080×1080 hasil crop — persis yang akan tayang.** Tampilkan semuanya sebagai carousel |
| `image_url` | = `image_urls[0]`. Dipertahankan agar konsumen lama tidak pecah |
| `carousel` | `true` bila lebih dari satu gambar |
| `photo_credits` | kredit fotografer foto tambahan (Pexels) |
| `hewan` | taxonomy artikel |
| `caption_instagram` | caption IG — **tanpa tautan** (link di caption IG tak bisa diklik) |
| `caption_facebook` | caption FB — **memuat permalink**, karena di FB bisa diklik |

⚠️ **Tampilkan `image_urls`, bukan gambar `.webp` di artikel.** Crop 1:1 bisa
memotong kepala hewan, dan itu baru kelihatan setelah di-crop — justru itu yang
perlu ditinjau.

✅ **Sejak 18 Agu 2026 janji "persis yang akan tayang" benar-benar berlaku:** saat
menayangkan, skrip memakai `image_urls` dari pratinjau **apa adanya**. Sebelumnya
foto tambahan dicari ULANG ke Pexels dan diverifikasi Gemini pada saat publish,
jadi yang naik bisa berbeda dari yang ditinjau — terukur: pratinjau berisi **1
foto**, yang tayang **4 foto**. Kalau salah satu foto pratinjau sudah tak bisa
diakses, skrip menghitung ulang sambil memperingatkan (lebih baik daripada gagal
di tengah Graph API) — hanya dalam kasus itu isinya bisa berbeda.

⚠️ **Caption IG dan FB sengaja berbeda.** Tampilkan keduanya terpisah; jangan
tampilkan satu lalu menganggap yang lain sama.

---

## 4. Tombol yang harus ada di panel

Panel Media Sosial minimal punya tiga tombol per kartu. Semuanya dipetakan ke satu
endpoint yang sama (`workflow_dispatch` pada `post-instagram.yml`), dibedakan input
`aksi`:

| Tombol | `aksi` | Efek |
|---|---|---|
| **Kirim / Terima** | `tayangkan` | posting ke IG + Halaman FB, lalu pratinjau dihapus dari antrean |
| **Tolak / Hapus** | `tolak` | pratinjau dibuang dari antrean, **tidak ada yang diposting** |
| **Segarkan pratinjau** | `pratinjau` | hitung ulang caption & foto (default) |

**Edit** bukan tombol terpisah: panel menyediakan kotak teks berisi
`caption_instagram` / `caption_facebook` dari pratinjau, lalu mengirim hasil
suntingannya lewat input `caption_ig` / `caption_fb` bersama `aksi: tayangkan`.
Kosongkan keduanya untuk memakai caption rakitan skrip.

⚠️ **Penyuntingan WAJIB terjadi sebelum tayang.** Caption Instagram tidak bisa
diubah lewat API setelah terbit — satu-satunya koreksi adalah hapus lalu posting
ulang manual dari aplikasi IG. Karena itu tombol Edit tidak punya padanan
"edit setelah tayang", dan panel sebaiknya tidak menjanjikannya.

`aksi: tolak` sengaja ditangani paling awal di skrip: ia tidak mengunduh foto dan
tidak memanggil Gemini sama sekali, jadi menolak itu murah.

## 5. Menayangkan

Picu `workflow_dispatch` pada `post-instagram.yml`:

```http
POST https://api.github.com/repos/centralcatgrooming-svg/blog-centralcats/actions/workflows/post-instagram.yml/dispatches
Authorization: Bearer <token dengan izin actions:write>
Content-Type: application/json

{
  "ref": "main",
  "inputs": {
    "path": "<path dari preview JSON>",
    "aksi": "tayangkan",
    "caption_ig": "<kosong = pakai rakitan skrip>",
    "caption_fb": "<kosong = pakai rakitan skrip>"
  }
}
```

- `aksi: "tayangkan"` → **benar-benar tayang** ke IG + Halaman FB.
  (`posting: "true"` masih diterima, sinonim.)
- `aksi: "pratinjau"` (default) → hanya menghitung ulang pratinjau.
- `aksi: "tolak"` → buang pratinjau dari antrean tanpa memposting.
- Nilainya **string**, bukan boolean — input `workflow_dispatch` selalu string.

🔴 Balasan `204 No Content` berarti workflow **berhasil diantre**, BUKAN berarti
sudah tayang — dan langkah postingnya `continue-on-error: true`, jadi run yang
gagal pun tetap berstatus hijau. Jangan pernah membaca 204 sebagai "beres".
Status sesungguhnya: pantau run terbaru workflow itu, atau anggap selesai ketika
`preview-<slug>.json` hilang dari antrean.

**Kewajiban panel selama menunggu** (ini bagian dari kontrak, bukan saran gaya):

1. Kunci tombol kartu itu begitu aksi dikirim — jangan biarkan tombolnya hidup
   lagi hanya karena `fetch` dispatch sudah selesai (itu terjadi dalam < 1 detik,
   sementara workflownya butuh menit).
2. Kuncinya bertahan melewati refresh halaman (simpan di `sessionStorage` atau
   sepadan). Kartu yang tombolnya hidup kembali = undangan posting ganda.
3. Muat ulang antrean **berkala sampai kartunya hilang** (mis. tiap 20 detik,
   maksimum ~6 menit), bukan sekali setelah 30 detik. Sekali-jalan **selalu**
   terlalu cepat dan membuat aksinya tampak gagal padahal berhasil.
4. Habis jendela tunggu tanpa perubahan → katakan apa adanya, jangan diam.

Skrip sekarang menolak posting kedua (lihat §2 `posted-<slug>.json`), tapi itu
jaring pengaman terakhir — panel tetap wajib tidak memancing kliknya.

**Menolak** cukup dengan `aksi: "tolak"` — skrip yang membuang asset-nya. Panel
tidak perlu izin `contents:write` sendiri.

---

## 6. Yang TIDAK akan muncul di antrean

Ini perilaku disengaja, bukan bug — jangan "diperbaiki" di sisi POS:

- 🔴 **Artikel di luar `SOCIAL_SECTIONS`** (default `kesehatan-hewan,panduan-tips,berita-tren`).
  Ini **ALLOWLIST**, bukan blocklist: section baru apa pun **otomatis tidak ikut
  tayang** sampai didaftarkan secara sadar. Sengaja gagal ke sisi aman — blocklist
  akan meloloskan tipe konten baru diam-diam (mis. rencana "Kisah Sukses" di
  `.ai/ROADMAP.md` Tahap 6).
  **`bisnis-hewan` DI LUAR medsos** (keputusan pemilik, 22 Agu 2026): materi peluang
  usaha menyangkut brand dan mengajari pesaing ⇒ konten **internal tim**. Di blog
  tetap terbit — kriteria blog memang sengaja lebih longgar.
- **Artikel bertag `bisnis`** (`SOCIAL_EXCLUDE_TAGS`). Lapis tambahan untuk artikel
  *Berita & Tren* (Sabtu = hari kucing ⇒ pasti tayang) yang mengambil sudut peluang
  usaha. Bergantung pada Gemini menuliskan tagnya, jadi **lapis pelengkap, bukan pagar utama**.
- **Artikel di luar `SOCIAL_ANIMALS`** (default `kucing,anjing`). Blog sengaja
  memuat semua hewan, medsos hanya dua ini. Artikel kelinci/hamster/burung tetap
  terbit di blog + push OneSignal + IndexNow, tapi tidak pernah masuk medsos.
- **Artikel tanpa `images`** — IG & FB wajib pakai gambar.
- **Artikel `draft = true`.**
- **Editan artikel lama.** Deteksi memakai `git diff --diff-filter=A`, jadi hanya
  file yang BARU DITAMBAHKAN. Menyunting artikel lama tidak menghasilkan pratinjau.

---

## 7. Catatan implementasi

- Batas carousel IG **2–10 gambar**; `CAROUSEL_MAX` default 4. Kalau hanya 1
  gambar yang lolos, skrip otomatis turun ke postingan foto tunggal.

  🔑 **`CAROUSEL_MAX` = BATAS ATAS, BUKAN TARGET.** Hasil **1, 2, 3, atau 4 foto
  sama sahnya**. Satu foto yang tepat lebih baik daripada empat yang dipaksakan;
  panel POS **tidak boleh** memperlakukan carousel pendek sebagai kegagalan.

  🔴 **Kenapa aturan ini ditulis (kejadian nyata 22 Agu 2026).** Pratinjau
  `peluang-bisnis-playground-kucing` berisi 4 foto: 1 rak dinding kucing (relevan)
  + **3 kucing di POHON OUTDOOR**, padahal artikelnya tentang playground *indoor*.
  Sebabnya bukan verifikasi yang mati, melainkan **verifikasi yang menanyakan hal
  yang salah**: subjeknya jatuh ke nama hewan (`"kucing"`), jadi Gemini hanya
  ditanya *"apakah foto ini menampilkan kucing?"* — dan kucing di pohon menjawab YA.
  Kata kunci `image_query = "cat climbing tree shelf"` membuat Pexels mengembalikan
  pohon sungguhan. Kedua lapis bekerja sesuai rancangan; yang bolong rancangannya:
  **nol lapis yang memeriksa kaitan foto dengan ISI artikel.**

  Sejak perbaikan: subjek verifikasi = `image_subject` bila ada, selain itu **JUDUL
  artikel** (deterministik, tidak bergantung Gemini mengisi front matter), dan
  `fetch_photos_bytes` **fail-closed** — tanpa subjek, foto tambahan tidak diambil
  sama sekali. Ada pula batas **10 panggilan verifikasi per artikel**: kuota habis
  ⇒ pulang dengan foto **lebih sedikit**, bukan dengan foto yang tidak diperiksa.
- Halaman Facebook memakai alur berbeda (unggah `published=false` lalu
  `attached_media` di `/feed`) — itu wajar, IG dan FB memang tak punya endpoint
  yang sama untuk multi-foto.
- Rujukan lengkap ada di `CLAUDE.md` Bagian 13 dan `scripts/post_instagram.py`.

---

## 8. Kontrak MATERI — apa yang boleh mengisi medsos (22 Agu 2026)

Sumber tunggal. Kalau tabel ini berbeda dari kode, **kodenya yang salah**.

### 8a. Pasokan mingguan — jaminan 4 posting

`WEEKDAY_SECTION` + `CAT_WEEKDAYS = {0,3,5}` + `HISTORY_WEEKDAYS = {6}` di
`scripts/generate_drafts.py`, 1 artikel/hari:

| Hari | Section blog | Hari kucing | Medsos | Pilar @centralcat_official |
|---|---|:--:|:--:|---|
| **Senin** | Kesehatan Hewan | ✅ | ✅ | Edukasi |
| Selasa | Panduan & Tips | — | bonus | Edukasi |
| **Rabu** | Bisnis Hewan | — | 🚫 **diblokir** | — *(internal tim)* |
| **Kamis** | Kesehatan Hewan | ✅ | ✅ | Edukasi |
| Jumat | Panduan & Tips | — | bonus | Edukasi |
| **Sabtu** | Berita & Tren | ✅ | ✅ | Berita |
| **Minggu** | Berita & Tren → *Ras & Sejarah* | ✅ (`hewan` dikunci) | ✅ | Sejarah |

⇒ **jaminan 4 posting/minggu** (Sen · Kam · Sab · Min); Sel/Jum bonus bila Gemini
kebetulan menulis kucing/anjing.

🔴 **Hari kucing dulu Rabu, dipindah ke Kamis 22 Agu 2026.** Sebabnya Rabu =
*Bisnis Hewan*, yang kini di luar kontrak materi — kalau Rabu dibiarkan jadi hari
kucing, ia menghasilkan artikel kucing yang tetap diblokir gerbang materi dan
**jaminan turun diam-diam 4 → 3**. **Jangan kembalikan ke `{0,2,5}`** tanpa lebih
dulu mengembalikan `bisnis-hewan` ke `SOCIAL_SECTIONS`.

⚠️ **Jangan hapus hari kucing ATAU slot Minggu tanpa mengganti yang lain** —
keduanya yang menjamin medsos terisi (blog CLAUDE.md Bagian 8 & 13).

### 8b. Kekuatan tiap sinyal — kenapa gerbangnya folder, bukan tag

🔑 **Aturan pokok: gerbang medsos TIDAK BOLEH bergantung pada keluaran Gemini.**

| Sinyal | Ditentukan siapa | Kekuatan | Perannya |
|---|---|---|---|
| **section / folder** | `WEEKDAY_SECTION` di skrip — **deterministik** | ✅ kuat | **gerbang utama** (allowlist) |
| `hewan = [...]` | Gemini (dipaksa `FORCE_CAT` di hari kucing) | ⚠️ sedang | filter hewan |
| `tags` memuat `bisnis` | **Gemini** — bisa lupa | ⚠️ lemah | lapis pelengkap |
| judul artikel | ditulis Gemini tapi **selalu ada** | ✅ cukup | subjek verifikasi foto |

### 8c. Foto

**1–4 foto, batas atas bukan target.** Tiap foto tambahan wajib lolos verifikasi
vision terhadap **judul/`image_subject`**, bukan sekadar nama hewan. Ragu, kuota
habis, atau tanpa subjek ⇒ **lebih sedikit foto**. Rinciannya di §7.

### 8d. Yang TIDAK berubah

Kadensi **tetap 4×/minggu** — yang dibenahi materinya, bukan frekuensinya.
Kriteria blog tetap longgar (semua hewan, bisnis boleh) dan **sengaja berbeda**
dari medsos. Perbedaan itu fitur, bukan inkonsistensi.

### 8e. Copywriting & hashtag caption medsos

Caption blog cukup mengajak **membaca**; caption medsos harus juga mengajak
**bertindak**. Susunannya:

```
{emoji topik} {judul}          <- baris 1: satu-satunya yang terbaca sebelum "selengkapnya"
{paragraf pembuka artikel}

📌 Yang dibahas:
• ...

{ajakan berkomentar}

━━━━━━━━━━━━━━
📖 Artikel lengkap → tautan di bio   (FB: tautan langsung)
📲 Booking grooming & cat hotel → WA <nomor>
📍 Pasar Kemis & Rajeg, Tangerang

{hashtag}
```

- **Emoji pembuka diturunkan dari subkategori** (`TOPIC_EMOJI`), **deterministik** —
  artikel yang sama selalu menghasilkan caption yang sama. Itu syarat mutlak agar
  pratinjau di panel POS benar-benar sama dengan yang tayang.
- **Blok CTA seluruhnya env** (`SOCIAL_CTA_WA` · `SOCIAL_CTA_LAYANAN` ·
  `SOCIAL_CTA_LOKASI`) — mengubah nomor/layanan/lokasi tidak boleh butuh commit.
- **Ekor (ajakan + CTA + hashtag) TIDAK PERNAH dipotong.** Kalau caption melebihi
  2.200 karakter, yang dipangkas bagian isinya.

🔴 **Hashtag — jaminan yang tidak boleh dilanggar (keputusan pemilik 22 Agu 2026):**

| Aturan | Nilai |
|---|---|
| **Wajib ada di setiap caption** | **`#centralcats`** dan **`#petshoptangerang`** (`MUST_TAGS`) |
| Minimal | **5** hashtag (`MIN_HASHTAGS`) |
| Maksimal | 20 (`MAX_HASHTAGS`) |
| Urutan | spesifik-artikel → hewan → komunitas → brand |

🔴 **Bentuk lama BISA MEMBUANG `#petshoptangerang` dan itu bukan hipotesis.**
Dulu daftarnya dirakit `tags + hewan + BRAND_TAGS` lalu dipotong `[:MAX_HASHTAGS]` —
brand ada di **urutan paling belakang**, jadi merekalah yang pertama hilang begitu
artikel punya banyak tag. Terbukti di uji: artikel bertag 25 kehilangan seluruh
hashtag brand. Sekarang **slot brand dipesan lebih dulu**, sisanya baru diisi tag
turunan artikel, plus tripwire yang memaksa `MUST_TAGS` masuk kalau sampai hilang.

⚠️ Menambah/mengurangi `BRAND_TAGS` **tidak** membatalkan jaminan ini — `MUST_TAGS`
sengaja dipisah supaya tetap terjamin walau daftar brand kelak dirapikan.
