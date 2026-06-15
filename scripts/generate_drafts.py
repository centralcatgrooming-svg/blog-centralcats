#!/usr/bin/env python3
"""
Pembuat draf artikel blog Central Cat's.

Fitur:
  - Jadwal per hari (otomatis pilih kategori sesuai hari, zona WIB):
      Senin & Kamis  -> Kesehatan Hewan
      Selasa & Jumat -> Panduan & Tips
      Rabu           -> Bisnis Hewan (peliharaan + ternak HALAL)
      Sabtu          -> Berita & Tren
      Minggu         -> libur (tidak membuat artikel)
  - Gambar: kategori "Berita & Tren" pakai FOTO asli (Pexels);
            kategori lain pakai ILUSTRASI/kartun (Pixabay).
  - Gemini menulis original, gaya answer-first, + FAQ (dipaksa via schema).
  - Output: file Markdown Hugo (draft=false) -> dijadikan Pull Request utk review.

Env:
  GEMINI_API_KEY  (wajib)
  PEXELS_API_KEY  (opsional) - foto asli utk berita
  PIXABAY_API_KEY (opsional) - ilustrasi/kartun utk non-berita
  NUM_ARTICLES    (opsional) - default 1
  SECTION         (opsional) - paksa kategori tertentu; "auto"/kosong = ikut hari
  GEMINI_MODEL    (opsional) - default gemini-2.5-flash
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
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
NUM = int(os.environ.get("NUM_ARTICLES", "1") or "1")
SECTION_OVERRIDE = (os.environ.get("SECTION", "") or "").strip()

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
    "bisnis-hewan": ["Peluang Usaha & Waralaba", "Tips Petshop & Grooming",
                     "Ternak & Budidaya (Halal)", "Industri & Pasar"],
}

# Hari (Senin=0 ... Minggu=6, WIB) -> kategori.
WEEKDAY_SECTION = {
    0: "kesehatan-hewan",   # Senin
    1: "panduan-tips",      # Selasa
    2: "bisnis-hewan",      # Rabu
    3: "kesehatan-hewan",   # Kamis
    4: "panduan-tips",      # Jumat
    5: "berita-tren",       # Sabtu
    6: None,                # Minggu (libur)
}

WIB = datetime.timezone(datetime.timedelta(hours=7))

SYSTEM = """Kamu penulis konten untuk blog Central Cat's — bisnis grooming, treatment kutu, cat hotel, dan petshop kucing di Tangerang (berdiri 2020). Pembaca adalah pemilik hewan peliharaan, terutama kucing (sering disebut "anabul").

ATURAN WAJIB:
1. Tulis konten 100% ORIGINAL dengan kata-katamu sendiri. JANGAN menyalin atau memparafrase ketat dari sumber mana pun.
2. Bahasa Indonesia yang hangat, ramah, jelas, dan mudah dipahami pemilik kucing awam. Boleh memakai istilah "anabul".
3. AKURAT. JANGAN mengarang statistik, angka, persentase, hasil studi, atau kutipan sumber. Jika tidak yakin pada sebuah fakta, sampaikan secara umum tanpa angka palsu.
4. Untuk topik KESEHATAN: bersifat edukasi umum saja. JANGAN memberi dosis obat spesifik, diagnosis pasti, atau resep medis. WAJIB menyarankan konsultasi ke dokter hewan untuk kondisi yang butuh penanganan, dan akhiri artikel kesehatan dengan kalimat saran konsultasi dokter hewan.
5. JANGAN membuat klaim berlebihan atau menyesatkan tentang produk maupun hasil.
6. SEO: judul jelas & menarik (idealnya <= 60 karakter), ringkasan memikat <= 150 karakter, gunakan subjudul (## dan ###) yang terstruktur, dan kata kunci yang muncul natural — TANPA keyword stuffing.
7. Tubuh artikel dalam Markdown, sekitar 600-1000 kata: paragraf pembuka, beberapa subjudul, poin praktis, dan kesimpulan singkat. JANGAN menulis judul utama sebagai H1 (#) di dalam body — judul sudah dipakai terpisah.
8. JAWAB LANGSUNG (penting untuk mesin pencari & asisten AI): paragraf PEMBUKA harus langsung menjawab inti pertanyaan/topik secara ringkas (definisi/jawaban inti dalam 2-3 kalimat pertama), baru diperdalam. Ini membantu artikel dikutip AI seperti ChatGPT, Gemini, dan Google AI Overviews.
9. Bila wajar, rumuskan judul & beberapa subjudul sebagai PERTANYAAN yang benar-benar diketik orang. Gunakan kalimat ringkas & mudah dipindai.
10. ATURAN HALAL (khusus kategori Bisnis Hewan): topik boleh mencakup hewan peliharaan dan ternak HALAL (mis. ayam, bebek, kambing, sapi, domba, kelinci, ikan, lebah madu). DILARANG KERAS mengangkat konten yang berpusat pada hewan haram dalam Islam (mis. babi/celeng) maupun budidaya/produk turunannya.
11. CAKUPAN HEWAN: kucing adalah TEMA UTAMA blog (mayoritas artikel), tetapi artikel BOLEH membahas hewan peliharaan lain (anjing, kelinci, hamster, burung, ikan, dll) bila relevan & bermanfaat — tidak harus selalu kucing. Sesuaikan isi dengan hewan yang dibahas.

Balas HANYA satu objek JSON valid dengan struktur:
{"title": "...", "slug": "...", "subcategory": "...", "tags": ["...","..."], "summary": "...", "image_query": "...", "body": "...", "faq": [{"q": "...", "a": "..."}]}
- "slug": huruf kecil, kata dipisah tanda hubung, tanpa spasi/tanda baca.
- "subcategory": pilih SATU dari daftar yang diberikan.
- "tags": 2-4 tag relevan (huruf kecil).
- "image_query": 2-4 kata BAHASA INGGRIS berupa OBJEK/ADEGAN KONKRET yang mudah ditemukan di situs foto/ilustrasi (mis. "cat drinking water", "fluffy cat grooming", "dog playing park", "rabbit eating", "chicken farm"). HINDARI istilah abstrak/medis yang tidak punya gambar (JANGAN mis. "urinary tract infection", "nutrition deficiency"). Query HARUS menampilkan HEWAN/SUBJEK UTAMA artikel ini secara konkret (kalau artikelnya tentang kucing pakai kucing, kalau tentang anjing pakai anjing, dst).
- "body": Markdown lengkap artikel (JANGAN masukkan FAQ ke body).
- "faq": 3-5 pasang tanya-jawab; jawaban ringkas 1-3 kalimat, akurat, satu baris. Topik kesehatan: sertakan anjuran dokter hewan bila relevan. JANGAN mengarang angka."""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "slug": {"type": "STRING"},
        "subcategory": {"type": "STRING"},
        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "summary": {"type": "STRING"},
        "image_query": {"type": "STRING"},
        "body": {"type": "STRING"},
        "faq": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"q": {"type": "STRING"}, "a": {"type": "STRING"}},
                "required": ["q", "a"],
            },
        },
    },
    "required": ["title", "slug", "subcategory", "tags", "summary", "image_query", "body", "faq"],
}


def pick_section():
    if SECTION_OVERRIDE and SECTION_OVERRIDE.lower() != "auto":
        if SECTION_OVERRIDE in SECTIONS:
            return SECTION_OVERRIDE
        print(f"(SECTION '{SECTION_OVERRIDE}' tidak dikenal, pakai jadwal hari)", file=sys.stderr)
    today = datetime.datetime.now(WIB).weekday()
    return WEEKDAY_SECTION.get(today)


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
    extra = ""
    if section == "bisnis-hewan":
        extra = ("Topik boleh bisnis hewan peliharaan ATAU ternak HALAL "
                 "(ayam, kambing, sapi, domba, kelinci, ikan, dll). DILARANG babi/hewan haram.\n")
    user = (
        f"Tulis SATU artikel blog original untuk kategori utama \"{SECTIONS[section]}\".\n"
        f"Pilih SATU subkategori dari: {subcats}.\n"
        f"{extra}"
        f"Pilih sendiri topik yang bermanfaat, relevan, dan SEGAR.\n"
        f"HINDARI topik yang mirip judul yang sudah ada: {avoid_txt}.\n"
        f"Patuhi semua ATURAN WAJIB. Balas HANYA JSON sesuai struktur."
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
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


def _save_webp(img_bytes, slug):
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    if HAS_PIL:
        out = IMG_DIR / f"{slug}.webp"
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if im.width > 1200:
            ratio = 1200 / float(im.width)
            im = im.resize((1200, int(im.height * ratio)), Image.LANCZOS)
        im.save(out, "webp", quality=80, method=6)
    else:
        out = IMG_DIR / f"{slug}.jpg"
        out.write_bytes(img_bytes)
    return f"/images/{out.name}"


def fetch_photo_pexels(query, slug):
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
        p = photos[0]
        src = p["src"].get("large2x") or p["src"].get("large") or p["src"]["original"]
        img = requests.get(src, timeout=60).content
        return _save_webp(img, slug), f"Foto: {p.get('photographer', 'Pexels')} / Pexels"
    except Exception as e:
        print(f"  (foto Pexels dilewati: {e})", file=sys.stderr)
        return None, None


def fetch_illustration_pixabay(query, slug):
    if not PIXABAY_KEY or not query:
        return None, None
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_KEY, "q": query, "image_type": "illustration",
                    "orientation": "horizontal", "safesearch": "true", "per_page": 3},
            timeout=60,
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return None, None
        h = hits[0]
        src = h.get("largeImageURL") or h.get("webformatURL")
        img = requests.get(src, timeout=60).content
        return _save_webp(img, slug), f"Ilustrasi: {h.get('user', 'Pixabay')} / Pixabay"
    except Exception as e:
        print(f"  (ilustrasi Pixabay dilewati: {e})", file=sys.stderr)
        return None, None


def fetch_image(query, slug, want_photo):
    """Berita & Tren -> foto asli (Pexels). Non-berita -> KONDISIONAL:
    coba ilustrasi (Pixabay) & foto (Pexels) bergantian acak, dengan saling fallback,
    supaya gambar bervariasi (kadang kartun, kadang foto) tapi tetap relevan."""
    if want_photo:
        path, credit = fetch_photo_pexels(query, slug)
        if not path:
            path, credit = fetch_illustration_pixabay(query, slug)
        return path, credit
    if random.choice([True, False]):
        path, credit = fetch_illustration_pixabay(query, slug)
        if not path:
            path, credit = fetch_photo_pexels(query, slug)
    else:
        path, credit = fetch_photo_pexels(query, slug)
        if not path:
            path, credit = fetch_illustration_pixabay(query, slug)
    return path, credit


def write_article(section, data):
    title = (data.get("title") or "Artikel Tanpa Judul").strip()
    slug = slugify(data.get("slug") or title)
    path = CONTENT / section / f"{slug}.md"
    if path.exists():
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        slug = f"{slug}-{stamp}"
        path = CONTENT / section / f"{slug}.md"

    want_photo = (section == "berita-tren")
    img_path, credit = fetch_image(data.get("image_query", ""), slug, want_photo)

    now = datetime.datetime.now(WIB)
    date_str = now.strftime("%Y-%m-%dT%H:%M:%S") + "+07:00"
    sub = (data.get("subcategory") or "").strip()
    tags = data.get("tags") or []
    tags_toml = ", ".join('"{}"'.format(str(t).replace('"', "")) for t in tags)
    summary = (data.get("summary") or "").replace('"', "'").strip()
    title_esc = title.replace('"', "'")
    body = (data.get("body") or "").strip()
    images_toml = f'"{img_path}"' if img_path else ""

    def _clean(s):
        return " ".join(str(s).split()).replace('"', "'").strip()
    faq_toml = ""
    for item in (data.get("faq") or []):
        q = _clean(item.get("q", "")) if isinstance(item, dict) else ""
        a = _clean(item.get("a", "")) if isinstance(item, dict) else ""
        if q and a:
            faq_toml += f'\n[[faq]]\nq = "{q}"\na = "{a}"\n'

    fm = (
        "+++\n"
        f'title = "{title_esc}"\n'
        f"date = {date_str}\n"
        "draft = false\n"
        f'categories = ["{sub}"]\n'
        f"tags = [{tags_toml}]\n"
        f'summary = "{summary}"\n'
        f"images = [{images_toml}]\n"
        f"{faq_toml}"
        "+++\n\n"
    )

    parts = [body]
    if img_path and credit:
        parts.append(f"\n\n---\n\n*{credit}*")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fm + "\n".join(parts) + "\n", encoding="utf-8")
    return path, bool(img_path)


def main():
    section = pick_section()
    if not section:
        print("Hari ini libur (Minggu, WIB) — tidak membuat artikel.")
        return
    print(f"Kategori hari ini: {SECTIONS[section]} ({section})")

    avoid = existing_titles()
    created = []
    for i in range(max(1, NUM)):
        try:
            data = gemini_article(section, avoid)
            p, has_img = write_article(section, data)
            avoid.append(data.get("title", ""))
            mark = "[img]" if has_img else "[teks]"
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
