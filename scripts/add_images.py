#!/usr/bin/env python3
"""Tambahkan GAMBAR ke artikel yang BELUM punya field `images` — TANPA mengubah
teks, slug, URL, atau tanggal artikel (non-destruktif). Output via Pull Request.

Memakai ulang fungsi dari generate_drafts.py (fetch_image foto-first + ANIMAL_EN)
agar konsisten dengan auto-draft: utamakan FOTO asli Pexels, ilustrasi Pixabay
hanya cadangan, dan query di-jangkar ke hewan utama.

Env yang dipakai:
- PEXELS_API_KEY, PIXABAY_API_KEY  -> sumber gambar.
- GEMINI_API_KEY                   -> TIDAK dipakai fitur ini, tetapi WAJIB diisi
                                      karena generate_drafts.py mengecek key ini
                                      saat di-import (sys.exit bila kosong).

Jalankan via workflow .github/workflows/add-images.yml (punya akses Secrets).
"""
import os
import re
import sys

import generate_drafts as g  # noqa: E402  (import meng-load konstanta + cek key)

# Mode GANTI FOTO satu artikel (dipakai saat foto lama ternyata keliru, mis. artikel
# ras yang kebagian foto ras lain). Berbeda dari mode normal, mode ini MENIMPA field
# `images` yang sudah ada — hanya untuk slug yang disebut eksplisit.
FORCE_SLUG = (os.environ.get("FORCE_SLUG", "") or "").strip()
FORCE_QUERY = (os.environ.get("FORCE_QUERY", "") or "").strip()
# Diisi -> tiap kandidat foto diverifikasi Gemini vision & TIDAK ada pelarian ke
# ilustrasi/foto generik (lihat generate_drafts.fetch_image strict=True).
FORCE_SUBJECT = (os.environ.get("FORCE_SUBJECT", "") or "").strip()

# Query gambar eksplisit (Inggris, relevan topik) untuk slug tertentu. Artikel lain
# memakai fallback = nama hewan utama (Inggris), mis. "cat".
QUERIES = {
    "tren-cat-hotel-2026": "cat hotel cattery",
    "memulai-usaha-petshop": "pet shop store",
    "5-tanda-bulu-kucing-sehat": "fluffy cat fur",
    "panduan-memandikan-kucing": "cat bath washing",
}

IMAGES_RE = re.compile(r'(?m)^\s*images\s*=\s*\[".+"\]\s*$')
# Versi untuk PENIMPAAN: sengaja pakai [ \t] bukan \s agar tidak ikut melahap
# baris kosong sesudahnya (\s mencakup newline) saat re.sub.
IMAGES_LINE_RE = re.compile(r'(?m)^[ \t]*images[ \t]*=[ \t]*\[".+"\][ \t]*$')
HEWAN_RE = re.compile(r'(?m)^\s*hewan\s*=\s*\[(.*?)\]')
# Front matter TOML: blok pertama di antara sepasang +++.
FRONTMATTER_RE = re.compile(r'^\+\+\+\s*\n.*?\n(\+\+\+)\s*$', re.S | re.M)


def primary_hewan(text):
    m = HEWAN_RE.search(text)
    if m:
        for h in re.findall(r'"([^"]+)"', m.group(1)):
            h = h.strip().lower()
            if h and h not in ("babi", "celeng"):
                return h
    return "kucing"


def build_query(slug, text):
    if slug in QUERIES:
        return QUERIES[slug]
    hewan = primary_hewan(text)
    return g.ANIMAL_EN.get(hewan, hewan)


def inject_images_line(text, img_path):
    """Sisipkan baris `images = [...]` tepat sebelum penutup +++ front matter."""
    m = FRONTMATTER_RE.search(text)
    if not m:
        return None
    at = m.start(1)
    return text[:at] + f'images = ["{img_path}"]\n' + text[at:]


def replace_images_line(text, img_path):
    """Timpa baris `images = [...]` yang sudah ada (khusus mode ganti foto)."""
    return IMAGES_LINE_RE.sub(lambda _m: f'images = ["{img_path}"]', text, count=1)


def force_one(slug, query, subject):
    """Ganti foto SATU artikel (walau sudah punya gambar). Nama file `.webp`
    mengikuti slug, jadi file lama ditimpa & URL artikel tidak berubah."""
    matches = [p for p in sorted(g.CONTENT.glob("*/*.md")) if p.stem == slug]
    if not matches:
        print(f"[GAGAL] artikel dengan slug '{slug}' tidak ditemukan", file=sys.stderr)
        return []
    path = matches[0]
    text = path.read_text(encoding="utf-8")
    q = query or build_query(slug, text)
    print(f"  {path.name}: query gambar \"{q}\""
          + (f", verifikasi subjek \"{subject}\"" if subject else ""), file=sys.stderr)

    img_path, credit = g.fetch_image([q], slug, subject=subject or None,
                                     strict=bool(subject))
    if not img_path:
        print(f"[LEWAT] {path.name}: tidak ada foto yang lolos verifikasi", file=sys.stderr)
        return []

    new_text = (replace_images_line(text, img_path) if IMAGES_RE.search(text)
                else inject_images_line(text, img_path))
    if not new_text:
        print(f"[LEWAT] {path.name}: front matter tak dikenali, batal", file=sys.stderr)
        return []
    path.write_text(new_text, encoding="utf-8")
    print(f"[OK] foto diganti: {path.relative_to(g.ROOT)} <- {img_path} ({credit})")
    return [str(path.relative_to(g.ROOT))]


def main():
    g.IMG_DIR.mkdir(parents=True, exist_ok=True)
    changed = []

    if FORCE_SLUG:
        changed = force_one(FORCE_SLUG, FORCE_QUERY, FORCE_SUBJECT)
        if not changed:
            print("Tidak ada perubahan.")
            return
        print("\nFoto diganti untuk:")
        for c in changed:
            print("  -", c)
        return

    for path in sorted(g.CONTENT.glob("*/*.md")):
        if path.name == "_index.md":
            continue
        text = path.read_text(encoding="utf-8")
        if IMAGES_RE.search(text):
            continue  # sudah punya gambar -> lewati

        slug = path.stem
        query = build_query(slug, text)
        print(f"  {path.name}: query gambar \"{query}\"", file=sys.stderr)
        # fetch_image() menerima DAFTAR query (spesifik -> umum). Wajib dibungkus
        # list: string yang dikirim langsung akan di-iterasi PER HURUF.
        img_path, credit = g.fetch_image([query], slug)
        if not img_path:
            print(f"[LEWAT] {path.name}: gambar tidak ditemukan", file=sys.stderr)
            continue

        new_text = inject_images_line(text, img_path)
        if not new_text:
            print(f"[LEWAT] {path.name}: front matter tak dikenali, batal", file=sys.stderr)
            continue

        path.write_text(new_text, encoding="utf-8")
        print(f"[OK] {path.relative_to(g.ROOT)} <- {img_path} ({credit})")
        changed.append(str(path.relative_to(g.ROOT)))

    if not changed:
        print("Tidak ada artikel yang perlu gambar. Tidak ada perubahan.")
        return
    print("\nGambar ditambahkan ke:")
    for c in changed:
        print("  -", c)


if __name__ == "__main__":
    main()
