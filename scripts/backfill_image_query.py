#!/usr/bin/env python3
"""Isi `image_query` / `image_query_fallback` / `image_subject` pada artikel LAMA.

Kenapa ada: carousel medsos (scripts/post_instagram.py) mencari foto tambahan
memakai kata kunci yang disimpan di front matter. Artikel yang dibuat SEBELUM
15 Agu 2026 belum punya field itu, jadi carousel-nya jatuh ke nama hewan saja
("cat") dan hasilnya kucing generik yang tidak nyambung ke topik artikel.
Skrip ini menurunkan kata kunci itu dari judul + isi artikel lewat Gemini.

NON-DESTRUKTIF: hanya MENAMBAH baris di front matter. Teks, slug, URL, tanggal,
`images`, dan blok `[[faq]]` tidak disentuh — jadi tidak ada artikel yang
berubah tampilannya di blog dan tidak ada URL yang mati. Output = Pull Request.

Aturan kata kuncinya SENGAJA disamakan dengan generate_drafts.py (lihat SYSTEM
prompt di sana): Inggris, 2-4 kata, WAJIB menyebut bagian tubuh/objek/adegan
yang jadi fokus artikel — bukan cuma nama hewannya. Istilah medis tanpa stok
foto (mis. "gastrointestinal stasis") harus diterjemahkan ke adegan yang
kelihatan (mis. "rabbit eating hay").

Env:
- GEMINI_API_KEY  -> wajib (dipakai langsung + dicek saat import generate_drafts).
- FORCE_SLUG      -> proses SATU artikel saja (uji). Kosong = semua yang belum punya.
- LIMIT           -> batas jumlah artikel per run (0/kosong = tanpa batas).

Jalankan via .github/workflows/backfill-image-query.yml.
"""
import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_drafts as g  # noqa: E402  (memuat konstanta + cek GEMINI_API_KEY)

FORCE_SLUG = (os.environ.get("FORCE_SLUG") or "").strip()
try:
    LIMIT = int(os.environ.get("LIMIT") or 0)
except ValueError:
    LIMIT = 0

# Front matter dibatasi +++ ... +++ (grup 1 = isi, grup 2 = penutup).
FM_RE = re.compile(r'^(\+\+\+\s*\n)(.*?\n)(\+\+\+\s*)$', re.S | re.M)
HAS_QUERY_RE = re.compile(r'(?m)^\s*image_query\s*=')
# Key yang disisipkan HARUS berada sebelum blok [[faq]]: di TOML, key setelah
# header array-of-tables ikut masuk ke tabel itu, jadi kalau ditaruh di bawah
# [[faq]] ia jadi field FAQ terakhir — bukan field artikel.
FAQ_RE = re.compile(r'(?m)^\s*\[\[faq\]\]')

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "image_query": {"type": "STRING"},
        "image_query_fallback": {"type": "STRING"},
    },
    "required": ["image_query", "image_query_fallback"],
}


def field(name, fm):
    m = re.search(r'(?m)^\s*%s\s*=\s*"(.*?)"\s*$' % re.escape(name), fm)
    return m.group(1).strip() if m else ""


def list_field(name, fm):
    m = re.search(r'(?m)^\s*%s\s*=\s*\[(.*?)\]\s*$' % re.escape(name), fm)
    if not m:
        return []
    return [x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip()]


def ask_gemini(title, summary, body, animal_en):
    user = (
        "Kamu membantu memilih KATA KUNCI PENCARIAN FOTO STOK (Pexels) untuk sebuah "
        "artikel blog hewan peliharaan.\n\n"
        f"Judul: {title}\n"
        f"Ringkasan: {summary}\n"
        f"Cuplikan isi: {body[:1200]}\n\n"
        "Balas HANYA JSON dengan dua field:\n"
        '- "image_query": 2-4 kata BAHASA INGGRIS untuk mencari FOTO yang BENAR-BENAR '
        "SESUAI ISI ARTIKEL — bukan foto hewan generik. WAJIB menyebut BAGIAN TUBUH, "
        "OBJEK, atau ADEGAN yang jadi fokus artikel. Contoh: artikel telinga kucing -> "
        '"cat ear close up" (BUKAN "cute cat"); artikel kucing di kandang jalan -> '
        '"cat inside carrier".\n'
        '- "image_query_fallback": 2-3 kata BAHASA INGGRIS, versi LEBIH UMUM tapi tetap '
        "relevan dan tetap menyebut hewannya. JANGAN sama persis dengan image_query.\n\n"
        "PENTING: istilah medis/abstrak yang tidak punya stok foto (mis. "
        '"gastrointestinal stasis", "hipertensi") HARUS diterjemahkan ke ADEGAN YANG '
        'KELIHATAN (mis. "rabbit eating hay", "cat at vet clinic").\n'
        f"Hewan utama artikel ini dalam bahasa Inggris: {animal_en}."
    )
    r = g.requests.post(
        g.GEMINI_URL,
        headers={"x-goog-api-key": g.GEMINI_KEY, "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 256,
                "responseMimeType": "application/json",
                "responseSchema": SCHEMA,
            },
        },
        timeout=90,
    )
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    return json.loads(text)


def anchor(q, animal_en):
    """Jangkar nama hewan ke query — sama seperti generate_drafts._anchor().
    Tanpa ini, query seperti "ear close up" bisa mengembalikan telinga manusia."""
    q = " ".join((q or "").split()).strip()
    if not q:
        return ""
    if re.search(r"\b" + re.escape(animal_en) + r"\b", q.lower()):
        return q
    return (animal_en + " " + q).strip()


def esc(s):
    return " ".join(str(s or "").split()).replace('"', "'").strip()


def process(path):
    text = path.read_text(encoding="utf-8")
    m = FM_RE.search(text)
    if not m:
        print(f"  [LEWAT] {path.name}: front matter tak dikenali")
        return False
    fm = m.group(2)
    if HAS_QUERY_RE.search(fm):
        return False  # sudah punya, jangan ditimpa

    title = field("title", fm)
    if not title:
        print(f"  [LEWAT] {path.name}: tanpa title")
        return False
    animals = [a.lower() for a in list_field("hewan", fm)] or ["kucing"]
    animal_en = g.ANIMAL_EN.get(animals[0], animals[0])

    body = text[m.end():]
    try:
        data = ask_gemini(title, field("summary", fm), body.strip(), animal_en)
    except Exception as e:
        print(f"  [GAGAL] {path.name}: {e}")
        return False

    q1 = anchor(data.get("image_query"), animal_en)
    q2 = anchor(data.get("image_query_fallback"), animal_en)
    if not q1:
        print(f"  [LEWAT] {path.name}: Gemini tidak memberi query")
        return False
    # Artikel ras ("Ras & Sejarah") butuh subjek verifikasi vision agar foto
    # carousel tidak jadi ras lain — kesalahan faktual, bukan sekadar kurang pas.
    subject = title if g.HISTORY_SUBCAT in list_field("categories", fm) else ""

    block = (f'image_query = "{esc(q1)}"\n'
             f'image_query_fallback = "{esc(q2)}"\n'
             f'image_subject = "{esc(subject)}"\n')

    faq = FAQ_RE.search(fm)
    at = faq.start() if faq else len(fm)
    new_fm = fm[:at] + block + fm[at:]
    path.write_text(m.group(1) + new_fm + m.group(3) + text[m.end():],
                    encoding="utf-8")
    print(f"  [OK] {path.name}\n       query    : {q1}\n       fallback : {q2}"
          + (f"\n       subjek   : {subject}" if subject else ""))
    return True


def main():
    files = [p for p in sorted(g.CONTENT.glob("*/*.md")) if p.stem != "_index"]
    if FORCE_SLUG:
        files = [p for p in files if p.stem == FORCE_SLUG]
        if not files:
            sys.exit(f"artikel dengan slug '{FORCE_SLUG}' tidak ditemukan")

    changed = 0
    for p in files:
        if LIMIT and changed >= LIMIT:
            print(f"(batas {LIMIT} artikel tercapai — sisanya dilewati)")
            break
        if process(p):
            changed += 1

    print(f"\nSelesai. {changed} artikel dilengkapi kata kunci gambar.")
    if not changed:
        print("Tidak ada perubahan.")


if __name__ == "__main__":
    main()
