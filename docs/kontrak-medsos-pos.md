# Kontrak data: panel "Media Sosial" di POS Pusat Konten

Dokumen ini adalah **kontrak antara repo blog (produsen) dan repo POS (konsumen)**
untuk panel Media Sosial di `https://app.centralcats.id/technology-system`.

Sisi blog **sudah jadi**: tiap artikel baru otomatis menghasilkan pratinjau, dan
tidak ada apa pun yang tayang ke Instagram/Facebook tanpa perintah eksplisit.
Sisi POS **belum dibangun** (per 15 Agu 2026 panelnya masih "Segera Hadir").

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

⚠️ **Caption IG dan FB sengaja berbeda.** Tampilkan keduanya terpisah; jangan
tampilkan satu lalu menganggap yang lain sama.

---

## 4. Menayangkan

Picu `workflow_dispatch` pada `post-instagram.yml`:

```http
POST https://api.github.com/repos/centralcatgrooming-svg/blog-centralcats/actions/workflows/post-instagram.yml/dispatches
Authorization: Bearer <token dengan izin actions:write>
Content-Type: application/json

{
  "ref": "main",
  "inputs": {
    "path": "<path dari preview JSON>",
    "posting": "true"
  }
}
```

- `posting: "true"` → **benar-benar tayang** ke IG + Halaman FB.
- `posting: "false"` (default) → hanya menghitung ulang pratinjau. Pakai ini
  untuk tombol "Segarkan pratinjau".
- Nilainya **string**, bukan boolean — input `workflow_dispatch` selalu string.

Balasan `204 No Content` berarti workflow *dijadwalkan*, **bukan** berarti sudah
tayang. Untuk status sesungguhnya, pantau run terbaru workflow itu, atau cukup
anggap selesai ketika `preview-<slug>.json` hilang dari antrean.

**Menolak/melewati** cukup dengan tidak memicu apa pun. Kalau ingin membuang dari
antrean tanpa memposting, hapus asset-nya:
`DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` (butuh `contents:write`).

---

## 5. Yang TIDAK akan muncul di antrean

Ini perilaku disengaja, bukan bug — jangan "diperbaiki" di sisi POS:

- **Artikel di luar `SOCIAL_ANIMALS`** (default `kucing,anjing`). Blog sengaja
  memuat semua hewan, medsos hanya dua ini. Artikel kelinci/hamster/burung tetap
  terbit di blog + push OneSignal + IndexNow, tapi tidak pernah masuk medsos.
- **Artikel tanpa `images`** — IG & FB wajib pakai gambar.
- **Artikel `draft = true`.**
- **Editan artikel lama.** Deteksi memakai `git diff --diff-filter=A`, jadi hanya
  file yang BARU DITAMBAHKAN. Menyunting artikel lama tidak menghasilkan pratinjau.

---

## 6. Catatan implementasi

- Batas carousel IG **2–10 gambar**; `CAROUSEL_MAX` default 4. Kalau hanya 1
  gambar yang lolos, skrip otomatis turun ke postingan foto tunggal.
- Halaman Facebook memakai alur berbeda (unggah `published=false` lalu
  `attached_media` di `/feed`) — itu wajar, IG dan FB memang tak punya endpoint
  yang sama untuk multi-foto.
- Rujukan lengkap ada di `CLAUDE.md` Bagian 13 dan `scripts/post_instagram.py`.
