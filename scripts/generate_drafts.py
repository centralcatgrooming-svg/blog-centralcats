#!/usr/bin/env python3
"""
Pembuat draf artikel blog Central Cat's.

Alur:
  1. Gemini (gratis) menulis artikel original sesuai aturan ketat (lihat SYSTEM).
  2. Pexels (gratis) mengambil 1 foto relevan, di-resize + dikonversi ke WebP.
  3. Artikel ditulis sebagai file Markdown Hugo ke content/<kategori>/.
  4. File ini lalu dijadikan Pull Request oleh workflow -> Anda tinjau & Merge untuk tayang.

Env yang dipakai:
  GEMINI_API_KEY  (wajib)   - kunci Gemini dari GitHub Secrets
  PEXELS_API_KEY  (opsional)- kunci Pexels; tanpa ini artikel dibuat tanpa gambar
  NUM_ARTICLES    (opsional)- jumlah artikel, default 1
  GEMINI_MODEL    (opsional)- default gemini-2.5-flash
"""

import os
import re
import io
import sys
import json
import random
import datetime
import pathlib

try:
    import requests
except ImportError:
    sys.exit("Paket 'requests' belum terpasang. Jalankan: pip install requests")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
NUM = int(os.environ.get("NUM_ARTICLES", "1") or "1")

if not GEMINI_KEY:
    sys.exit("GEMINI_API_KEY belum diset (cek GitHub Secrets).")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
IMG_DIR = ROOT / "static" / "images"

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SECTIONS = {
    "kesehatan-hewan": "Kesehatan Hewan",
    "panduan-tips": "Panduan & Tips",
    "berita-tren": "Berita & Tren",
    "bisnis-hewan": "Bisnis Hewan Peliharaan",
}

SUBCATS = {
    "kesehatan-hewan": ["Kesehatan Kucing", "Nutrisi & Makanan",
                        "Penyakit & Pencegahan", "Grooming & Perawatan"],
    "panduan-tips": ["Panduan Pemula", "Perawatan Harian"],
    "berita-tren": ["Tren & Lifestyle", "Event & Komunitas"],
    "bisnis-hewan": ["Peluang Usaha & Waralaba", "Tips Petshop & Grooming", "Industri & Pasar"],
}

# ===================== ATURAN PEMBUATAN ARTIKEL =====================
SYSTEM = """Kamu penulis konten untuk blog Central Cat's — bisnis grooming, treatment kutu, cat hotel, dan petshop kucing di Tangerang (berdiri 2020). Pembaca adalah pemilik hewan peliharaan, terutama kucing (sering disebut "anabul").

ATURAN WAJIB:
1. Tulis konten 100% ORIGINAL dengan kata-katamu sendiri. JANGAN menyalin atau memparafrase ketat dari sumber mana pun.
2. Bahasa Indonesia yang hangat, ramah, jelas, dan mudah dipahami pemilik kucing awam. Boleh memakai istilah "anabul".
3. AKURAT. JANGAN mengarang statistik, angka, persentase, hasil studi, atau kutipan sumber. Jika tidak yakin pada sebuah fakta, sampaikan secara umum tanpa angka palsu.
4. Untuk topik KESEHATAN: bersifat edukasi umum saja. JANGAN memberi dosis obat spesifik, diagnosis pasti, atau resep medis. WAJIB menyarankan konsultasi ke dokter hewan untuk kondisi yang butuh penanganan, dan akhiri artikel kesehatan dengan kalimat saran konsultasi dokter hewan.
5. JANGAN membuat klaim berlebihan atau menyesatkan tentang produk maupun hasil.
6. SEO: judul jelas & menarik (idealnya <= 60 karakter), ringkasan memikat <= 150 karakter, gunakan subjudul (## dan ###) yang terstruktur, dan kata kunci yang muncul natural — TANPA keyword stuffing.
7. Tubuh artikel dalam Markdown, sekitar 600-1000 kata: paragraf pembuka, beberapa subjudul, poin praktis, dan kesimpulan singkat. JANGAN menulis judul utama sebagai H1 (#) di dalam body — judul sudah dipakai terpisah.

Balas HANYA satu objek JSON valid dengan struktur:
{"title": "...", "slug": "...", "subcategory": "...", "tags": ["...","..."], "summary": "...", "image_query": "...", "body": "..."}
- "slug": huruf kecil, kata dipisah tanda hubung, tanpa spasi/tanda baca.
- "subcategory": pilih SATU dari daftar yang diberikan.
- "tags": 2-4 tag relevan (huruf kecil).
- "image_query": 2-4 kata kunci dalam BAHASA INGGRIS untuk mencari foto pendukung di stok foto (mis. "persian cat grooming", "cat eating food", "kitten playing"). Pilih yang relevan dengan isi artikel.
- "body": Markdown lengkap artikel."""


def slugify(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:80] or "artikel"


def existing_titles():
    titles = []
    if not CONTENT.exists():
        return titles
    for p in CONTENT.rglob("*.md"):
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r'title\s*=\s*"([^"]+)"', txt) or re.search(r'^title:\s*"?([^"\n]+)"?', txt, re.M)
        if m:
            titles.append(m.group(1).strip())
    return titles


def gemini_article(section, avoid):
    subcats = SUBCATS[section]
    avoid_txt = "; ".join(avoid[-40:]) if avoid else "(belum ada)"
    user = (
        f"Tulis SATU artikel blog original untuk kategori utama \"{SECTIONS[section]}\".\n"
        f"Pilih SATU subkategori dari: {subcats}.\n"
        f"Pilih sendiri topik yang bermanfaat, relevan untuk pemilik kucing, dan SEGAR.\n"
        f"HINDARI topik yang mirip judul yang sudah ada: {avoid_txt}.\n"
        f"Patuhi semua ATURAN WAJIB. Balas HANYA JSON sesuai struktur."
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    r = requests.post(
        GEMINI_URL,
        headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    return json.loads(text)


def fetch_image(query, slug):
    """Cari foto di Pexels, resize + konversi WebP. Return (web_path, credit) atau (None, None)."""
    if not PEXELS_KEY or not query:
        return None, None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=60,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None, None
        photo = photos[0]
        src = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"]["original"]
        photographer = photo.get("photographer", "Pexels")

        img_bytes = requests.get(src, timeout=60).content
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        out = IMG_DIR / f"{slug}.webp"

        if HAS_PIL:
            im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            max_w = 1200
            if im.width > max_w:
                ratio = max_w / float(im.width)
                im = im.resize((max_w, int(im.height * ratio)), Image.LANCZOS)
            im.save(out, "webp", quality=80, method=6)
        else:
            # Tanpa Pillow: simpan apa adanya (fallback)
            out = IMG_DIR / f"{slug}.jpg"
            out.write_bytes(img_bytes)

        return f"/images/{out.name}", photographer
    except Exception as e:
        print(f"  (gambar dilewati: {e})", file=sys.stderr)
        return None, None


def write_article(section, data):
    title = (data.get("title") or "Artikel Tanpa Judul").strip()
    slug = slugify(data.get("slug") or title)
    path = CONTENT / section / f"{slug}.md"
    if path.exists():
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        slug = f"{slug}-{stamp}"
        path = CONTENT / section / f"{slug}.md"

    img_path, credit = fetch_image(data.get("image_query", ""), slug)

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%dT%H:%M:%S") + "+07:00"
    sub = (data.get("subcategory") or "").strip()
    tags = data.get("tags") or []
    tags_toml = ", ".join('"{}"'.format(str(t).replace('"', "")) for t in tags)
    summary = (data.get("summary") or "").replace('"', "'").strip()
    title_esc = title.replace('"', "'")
    body = (data.get("body") or "").strip()
    images_toml = f'"{img_path}"' if img_path else ""

    fm = (
        "+++\n"
        f'title = "{title_esc}"\n'
        f"date = {date_str}\n"
        "draft = false\n"
        f'categories = ["{sub}"]\n'
        f"tags = [{tags_toml}]\n"
        f'summary = "{summary}"\n'
        f"images = [{images_toml}]\n"
        "+++\n\n"
    )

    # Catatan: gambar utama TIDAK disisipkan ke body karena template (single.html)
    # sudah menampilkan front matter `images` sebagai gambar utama. Menyisipkan di
    # body akan membuat foto tampil dobel. Hanya kredit foto yang ditambahkan.
    parts = [body]
    if img_path and credit:
        parts.append(f"\n\n---\n\n*Foto: {credit} / Pexels*")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fm + "\n".join(parts) + "\n", encoding="utf-8")
    return path, bool(img_path)


def main():
    avoid = existing_titles()
    sections = list(SECTIONS.keys())
    created = []
    for i in range(max(1, NUM)):
        section = random.choice(sections)
        try:
            data = gemini_article(section, avoid)
            p, has_img = write_article(section, data)
            avoid.append(data.get("title", ""))
            mark = "🖼️" if has_img else "📄"
            created.append(str(p.relative_to(ROOT)))
            print(f"[OK] {mark} {p.relative_to(ROOT)}")
        except Exception as e:
            print(f"[GAGAL] artikel ke-{i+1}: {e}", file=sys.stderr)

    if not created:
        sys.exit("Tidak ada artikel yang berhasil dibuat.")
    print("\nArtikel dibuat (menunggu review lewat Pull Request):")
    for c in created:
        print("  -", c)


if __name__ == "__main__":
    main()
