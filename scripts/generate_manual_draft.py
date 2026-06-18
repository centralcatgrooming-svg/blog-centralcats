#!/usr/bin/env python3
"""
Pembuat draf artikel MANUAL ("Tulis Manual" dari Pusat Konten POS).

Alur: POS upload gambar + manifest.json ke Supabase Storage (bucket blog-manual),
lalu dispatch workflow manual-draft.yml dengan input manifest_url. Skrip ini:
  1. Ambil manifest.json (judul opsional, kategori, tone, bahan, images[]).
  2. Gemini MERAPIKAN bahan penulis jadi artikel utuh (patuhi ATURAN WAJIB blog).
  3. Unduh + proses gambar penulis -> webp <=1600px q80 di static/images/<slug>/NN.webp.
  4. Gambar #1 = COVER (front matter images=[...]); sisanya GALERI di badan (urut upload).
  5. Tulis content/<kategori>/<slug>.md -> dijadikan Pull Request (label ai-draft).

Memakai ulang konstanta/fungsi dari generate_drafts.py (SYSTEM, RESPONSE_SCHEMA,
slugify, SECTIONS, SUBCATS) supaya gaya & front matter konsisten dgn auto-draft.

Env:
  GEMINI_API_KEY  (wajib) - dipakai generate_drafts saat di-import + untuk Gemini.
  MANIFEST_URL    (wajib) - URL public manifest.json di Supabase Storage.
  JOB_ID          (opsional) - untuk log.
"""
import os
import re
import io
import sys
import json
import datetime
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    sys.exit("Paket 'requests' belum terpasang. Jalankan: pip install requests")

import generate_drafts as g  # reuse SYSTEM/schema/slugify/SECTIONS (cek GEMINI_API_KEY saat import)

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Dukungan foto HEIC/HEIF (default kamera iPhone) agar tidak gagal saat dibuka PIL.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

MANIFEST_URL = (os.environ.get("MANIFEST_URL") or "").strip()
JOB_ID = (os.environ.get("JOB_ID") or "").strip()

# Hanya terima manifest/gambar dari host Supabase ini (cegah SSRF via input dispatch).
ALLOWED_HOST = "vjjuqllkycokgpidtlmw.supabase.co"

TONE_HINT = {
    "hangat": "hangat, ramah, akrab (boleh sebut 'anabul')",
    "santai": "santai & ringan, mengalir seperti ngobrol",
    "profesional": "profesional, rapi, tetap mudah dipahami",
    "edukatif": "edukatif & informatif, terstruktur dengan poin jelas",
}

MAX_IMAGES = 10


def fetch_manifest(url):
    if not url:
        sys.exit("MANIFEST_URL belum diset.")
    host = urlparse(url).hostname or ""
    if host != ALLOWED_HOST:
        sys.exit(f"Host manifest tidak diizinkan: {host}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def gemini_manual(judul, kategori, tone, bahan):
    subcats = g.SUBCATS[kategori]
    tone_txt = TONE_HINT.get((tone or "").lower(), TONE_HINT["hangat"])
    extra = ""
    if kategori == "bisnis-hewan":
        extra = "Topik boleh bisnis hewan peliharaan ATAU ternak HALAL. DILARANG babi/hewan haram.\n"
    judul_line = (
        f'Judul yang diinginkan penulis: "{judul}". Pakai/rapikan judul ini (boleh '
        f'diperhalus untuk SEO) — JANGAN ganti topik.\n'
        if (judul or "").strip()
        else "Buatkan judul yang jelas & menarik (<=60 karakter) dari bahan.\n"
    )
    user = (
        "Penulis tim Central Cat's memberikan BAHAN/CATATAN mentah untuk dijadikan "
        "SATU artikel blog yang rapi & enak dibaca.\n"
        f'Kategori utama: "{g.SECTIONS[kategori]}". Pilih SATU subkategori dari: {subcats}.\n'
        f"Nada/gaya tulisan yang diinginkan: {tone_txt}.\n"
        f"{extra}"
        f"{judul_line}"
        "\nRapikan & kembangkan BAHAN berikut menjadi artikel utuh & terstruktur "
        "(perbaiki tata bahasa, tambah subjudul, alur, dan kesimpulan). Setia pada "
        "maksud & fakta yang diberikan penulis — JANGAN mengarang fakta/angka/statistik "
        "baru, dan JANGAN keluar dari topik bahan.\n"
        f'BAHAN:\n"""\n{bahan}\n"""\n\n'
        "Patuhi semua ATURAN WAJIB. Balas HANYA JSON sesuai struktur."
    )
    payload = {
        "system_instruction": {"parts": [{"text": g.SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "responseSchema": g.RESPONSE_SCHEMA,
        },
    }
    r = requests.post(
        g.GEMINI_URL,
        headers={"x-goog-api-key": g.GEMINI_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    return json.loads(text)


def process_images(image_urls, slug):
    """Unduh + konversi gambar penulis ke webp <=1600px q80 di static/images/<slug>/NN.webp.
    Return list path publik ('/images/<slug>/NN.webp') urut input. Gambar gagal dilewati."""
    if not image_urls:
        return []
    dest = g.IMG_DIR / slug
    dest.mkdir(parents=True, exist_ok=True)
    out_paths = []
    idx = 0
    for url in image_urls[:MAX_IMAGES]:
        host = urlparse(url).hostname or ""
        if host != ALLOWED_HOST:
            print(f"  (lewati gambar, host tak diizinkan: {host})", file=sys.stderr)
            continue
        try:
            raw = requests.get(url, timeout=90).content
        except Exception as e:
            print(f"  (lewati gambar, gagal unduh: {e})", file=sys.stderr)
            continue
        idx += 1
        try:
            if HAS_PIL:
                name = f"{idx:02d}.webp"
                out = dest / name
                im = Image.open(io.BytesIO(raw))
                im = ImageOps.exif_transpose(im)  # hormati orientasi foto HP
                im = im.convert("RGB")
                if im.width > 1600:
                    ratio = 1600 / float(im.width)
                    im = im.resize((1600, int(im.height * ratio)), Image.LANCZOS)
                im.save(out, "webp", quality=80, method=6)
            else:
                name = f"{idx:02d}.jpg"
                out = dest / name
                out.write_bytes(raw)
            out_paths.append(f"/images/{slug}/{out.name}")
        except Exception as e:
            print(f"  (lewati gambar, gagal proses: {e})", file=sys.stderr)
            idx -= 1
            continue
    return out_paths


def _clean(s):
    return " ".join(str(s).split()).replace('"', "'").strip()


def write_article(kategori, data, image_paths, img_slug):
    title = (data.get("title") or "Artikel Tanpa Judul").strip()
    slug = g.slugify(data.get("slug") or title)
    path = g.CONTENT / kategori / f"{slug}.md"
    if path.exists():
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        path = g.CONTENT / kategori / f"{slug}-{stamp}.md"

    now = datetime.datetime.now(g.WIB)
    date_str = now.strftime("%Y-%m-%dT%H:%M:%S") + "+07:00"
    sub = (data.get("subcategory") or "").strip()
    tags = data.get("tags") or []
    tags_toml = ", ".join('"{}"'.format(str(t).replace('"', "")) for t in tags)

    def _hslug(s):
        s = re.sub(r"[^a-z0-9\s-]", "", (str(s) or "").lower())
        return re.sub(r"\s+", "-", s).strip("-")
    hewan_raw = data.get("hewan") or []
    if isinstance(hewan_raw, str):
        hewan_raw = [hewan_raw]
    hewan_list = []
    for h in hewan_raw:
        hs = _hslug(h)
        if hs and hs not in ("babi", "celeng") and hs not in hewan_list:
            hewan_list.append(hs)
    if not hewan_list:
        hewan_list = ["kucing"]
    hewan_toml = ", ".join('"{}"'.format(h) for h in hewan_list)

    summary = (data.get("summary") or "").replace('"', "'").strip()
    title_esc = title.replace('"', "'")
    body = (data.get("body") or "").strip()

    cover = image_paths[0] if image_paths else ""
    images_toml = f'"{cover}"' if cover else ""

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
        "author = \"Team Central Cat's\"\n"
        f'categories = ["{sub}"]\n'
        f"tags = [{tags_toml}]\n"
        f"hewan = [{hewan_toml}]\n"
        f'summary = "{summary}"\n'
        f"images = [{images_toml}]\n"
        f"{faq_toml}"
        "+++\n\n"
    )

    parts = [body]
    # Galeri: gambar ke-2 dst ditaruh di BADAN artikel, urut upload.
    gallery = image_paths[1:]
    if gallery:
        gal_md = "\n\n".join(f"![{title_esc}]({p})" for p in gallery)
        parts.append("\n\n" + gal_md)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fm + "".join(parts) + "\n", encoding="utf-8")
    return path


def main():
    m = fetch_manifest(MANIFEST_URL)
    kategori = (m.get("kategori") or "").strip()
    if kategori not in g.SECTIONS:
        sys.exit(f"Kategori tidak valid: '{kategori}' (harus salah satu {list(g.SECTIONS)})")
    bahan = (m.get("bahan") or "").strip()
    if not bahan:
        sys.exit("Bahan kosong — tidak ada yang bisa dirapikan.")
    judul = (m.get("judul") or "").strip()
    tone = (m.get("tone") or "").strip()
    images = m.get("images") or []
    if not isinstance(images, list):
        images = []
    print(f"Job {JOB_ID or '-'} | kategori={kategori} | gambar={len(images)} | "
          f"judul={'(auto)' if not judul else judul}")

    data = gemini_manual(judul, kategori, tone, bahan)
    slug = g.slugify(data.get("slug") or judul or data.get("title") or "artikel")
    image_paths = process_images(images, slug)
    print(f"  Gambar diproses: {len(image_paths)} "
          f"(cover + {max(0, len(image_paths) - 1)} galeri)")
    path = write_article(kategori, data, image_paths, slug)
    print(f"[OK] {path.relative_to(g.ROOT)}")


if __name__ == "__main__":
    main()
