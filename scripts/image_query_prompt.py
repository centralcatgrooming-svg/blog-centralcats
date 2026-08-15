#!/usr/bin/env python3
"""Jalur PROMPT untuk kata kunci gambar — tanpa memanggil API AI sama sekali.

Alasannya: mengisi `image_query` lewat API Gemini kena kuota harian, dan langganan
ChatGPT (paket Go) TIDAK memberi akses API. Jadi manusia yang menjalankan model-nya
di ChatGPT, skrip ini cuma menyiapkan prompt dan menerima balasannya.

    MODE=prompt  -> cetak prompt berisi artikel yang belum punya image_query
                    (disalin ke ChatGPT)
    MODE=apply   -> baca JSON balasan dari env PAYLOAD, validasi, tulis ke
                    front matter, lalu (lewat workflow) buka Pull Request

NON-DESTRUKTIF: hanya MENAMBAH baris di front matter. Teks, slug, URL, tanggal,
`images`, dan blok `[[faq]]` tidak disentuh.

Penyisipan dilakukan SEBELUM blok `[[faq]]`: di TOML, key setelah header
array-of-tables ikut masuk ke tabel itu, jadi kalau ditaruh di bawah `[[faq]]`
ia jadi field FAQ terakhir — bukan field artikel.

Env:
- MODE           -> "prompt" (default) atau "apply".
- LIMIT          -> mode prompt: jumlah artikel per batch (default 20, 0 = semua).
- PAYLOAD        -> mode apply: JSON balasan ChatGPT.
- GEMINI_API_KEY -> TIDAK dipakai memanggil apa pun; wajib ada hanya karena
                    generate_drafts.py mengeceknya saat di-import (sama seperti
                    add_images.py). Yang dipakai dari sana cuma ANIMAL_EN &
                    HISTORY_SUBCAT.
"""
import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_drafts as g  # noqa: E402  (dipakai utk ANIMAL_EN & HISTORY_SUBCAT)

MODE = (os.environ.get("MODE") or "prompt").strip().lower()
PAYLOAD = os.environ.get("PAYLOAD") or ""
SLUG = (os.environ.get("SLUG") or "").strip()
try:
    LIMIT = int(os.environ.get("LIMIT") or 20)
except ValueError:
    LIMIT = 20

FM_RE = re.compile(r'^(\+\+\+\s*\n)(.*?\n)(\+\+\+\s*)$', re.S | re.M)
HAS_QUERY_RE = re.compile(r'(?m)^\s*image_query\s*=')
FAQ_RE = re.compile(r'(?m)^\s*\[\[faq\]\]')

ATURAN = """ATURAN (ikuti persis):
- Balas HANYA array JSON. Tanpa penjelasan, tanpa blok kode, tanpa teks lain.
- Tiap elemen: {"slug": "...", "image_query": "...", "image_query_fallback": "..."}
- "slug" WAJIB disalin persis dari daftar di bawah. Jangan mengarang slug baru.
- "image_query": 2-4 kata BAHASA INGGRIS untuk mencari FOTO STOK yang BENAR-BENAR
  SESUAI ISI ARTIKEL — bukan foto hewan generik. WAJIB menyebut BAGIAN TUBUH,
  OBJEK, atau ADEGAN yang jadi fokus artikel.
  Contoh: artikel telinga kucing -> "cat ear close up" (BUKAN "cute cat");
          artikel kucing di kandang jalan -> "cat inside carrier".
- "image_query_fallback": 2-3 kata BAHASA INGGRIS, versi LEBIH UMUM tapi tetap
  relevan dan tetap menyebut hewannya. JANGAN sama persis dengan image_query.
- Istilah medis/abstrak yang tidak punya stok foto (mis. "gastrointestinal stasis",
  "hipertensi") HARUS diterjemahkan ke ADEGAN YANG KELIHATAN
  (mis. "rabbit eating hay", "cat at vet clinic").
- Sebutkan hewannya dalam bahasa Inggris sesuai kolom "hewan" tiap artikel."""


# Prompt untuk MEMBUAT GAMBAR (bukan mencari foto stok). Dipakai saat stok foto
# memang tidak ada. Strukturnya sengaja mewajibkan LATAR dan ISI FRAME disebut
# eksplisit — prompt gambar tanpa itu menghasilkan komposisi acak yang tak nyambung.
ATURAN_GAMBAR = """Kamu membuat PROMPT PEMBUATAN GAMBAR untuk artikel blog hewan peliharaan.
Untuk SETIAP artikel di bawah, tulis SATU prompt gambar berbahasa Inggris yang LENGKAP.

Tiap prompt WAJIB memuat kedelapan unsur ini, berurutan, dipisah koma:
1. SUBJEK    - hewan apa, ras/warna bila relevan, usia (anak/dewasa).
2. AKSI      - apa yang sedang dilakukan, sesuai topik artikel.
3. FOKUS     - bagian tubuh/objek yang jadi inti artikel dan harus terlihat jelas.
4. LATAR     - latar belakang konkret (mis. ruang tamu rumah, meja periksa klinik
               hewan, kandang beralas jerami, halaman berumput). JANGAN "latar polos"
               kecuali topiknya memang menuntut.
5. ELEMEN    - benda pendukung yang harus ada di frame (mis. mangkuk, sisir, litter
               box, jerami). Sebut maksimal 3 supaya tidak berantakan.
6. CAHAYA    - mis. cahaya alami dari jendela, cahaya lembut merata.
7. KOMPOSISI - sudut & jarak (mis. close-up setinggi mata, medium shot), plus
               "square 1:1 composition" karena dipakai untuk carousel Instagram.
8. GAYA      - "photorealistic photograph, natural colors, sharp focus".

WAJIB ditambahkan di akhir tiap prompt, apa adanya:
"anatomically correct animal, correct number of toes and limbs, no text, no watermark,
no logo, no human face"

ATURAN KELUARAN:
- Balas HANYA array JSON. Tanpa penjelasan, tanpa blok kode.
- Tiap elemen: {"slug": "...", "image_prompt": "..."}
- "slug" WAJIB disalin persis dari daftar. Jangan mengarang slug baru.
- JANGAN membuat gambar yang memperlihatkan luka, darah, atau hewan tampak
  menderita — artikel kesehatan tetap harus nyaman dilihat pemilik hewan."""


def field(name, fm):
    m = re.search(r'(?m)^\s*%s\s*=\s*"(.*?)"\s*$' % re.escape(name), fm)
    return m.group(1).strip() if m else ""


def list_field(name, fm):
    m = re.search(r'(?m)^\s*%s\s*=\s*\[(.*?)\]\s*$' % re.escape(name), fm)
    if not m:
        return []
    return [x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip()]


def anchor(q, animal_en):
    """Jangkar nama hewan ke query — sama seperti generate_drafts._anchor().
    Tanpa ini, "ear close up" bisa mengembalikan telinga manusia."""
    q = " ".join((q or "").split()).strip()
    if not q:
        return ""
    if re.search(r"\b" + re.escape(animal_en) + r"\b", q.lower()):
        return q
    return (animal_en + " " + q).strip()


def esc(s):
    return " ".join(str(s or "").split()).replace('"', "'").strip()


def pending():
    """Artikel yang belum punya image_query, beserta front matter-nya."""
    out = []
    for p in sorted(g.CONTENT.glob("*/*.md")):
        if p.stem == "_index":
            continue
        m = FM_RE.search(p.read_text(encoding="utf-8"))
        if not m or HAS_QUERY_RE.search(m.group(2)):
            continue
        out.append((p, m.group(2)))
    return out


def daftar_artikel(items):
    """Baris deskripsi tiap artikel — dipakai kedua jenis prompt."""
    baris = []
    for p, fm in items:
        animals = [a.lower() for a in list_field("hewan", fm)] or ["kucing"]
        animal_en = g.ANIMAL_EN.get(animals[0], animals[0])
        baris.append(
            f'- slug: {p.stem}\n'
            f'  judul: {field("title", fm)}\n'
            f'  hewan: {animal_en}\n'
            f'  ringkasan: {field("summary", fm)}'
        )
    return baris


def keluarkan(judul, teks, petunjuk):
    print(teks)
    # Job summary = tempat paling nyaman untuk menyalin (dirender rapi di UI Actions).
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## {judul}\n\n{petunjuk}\n\n```\n{teks}\n```\n")


def do_prompt():
    items = pending()
    total = len(items)
    if not total:
        print("Semua artikel sudah punya image_query — tidak ada yang perlu diproses.")
        return
    if LIMIT:
        items = items[:LIMIT]

    teks = (f"{ATURAN}\n\nDaftar artikel ({len(items)} dari {total} yang belum terisi):\n\n"
            + "\n".join(daftar_artikel(items)) + "\n")
    keluarkan(f"Prompt kata kunci gambar ({len(items)} dari {total} artikel)", teks,
              "Salin blok di bawah, tempel ke ChatGPT, lalu tempel balasannya ke input "
              "`payload` saat menjalankan workflow ini dengan `mode: apply`.")


def do_prompt_gambar():
    """Prompt untuk MEMBUAT gambar, bukan mencarinya. Tidak menyentuh front matter —
    hasilnya berupa gambar yang Anda buat sendiri di ChatGPT, lalu dimasukkan lewat
    "Tulis Manual" di POS (jalur itu sudah mendukung cover + galeri)."""
    items = pending()
    if SLUG:
        items = [(p, fm) for p, fm in items if p.stem == SLUG]
        if not items:
            # Artikel yang sudah punya image_query tetap boleh dibuatkan prompt gambar.
            for p in g.CONTENT.glob("*/*.md"):
                if p.stem == SLUG:
                    m = FM_RE.search(p.read_text(encoding="utf-8"))
                    if m:
                        items = [(p, m.group(2))]
            if not items:
                sys.exit(f"artikel dengan slug '{SLUG}' tidak ditemukan")
    elif LIMIT:
        items = items[:LIMIT]
    if not items:
        print("Tidak ada artikel yang cocok.")
        return

    teks = (f"{ATURAN_GAMBAR}\n\nDaftar artikel ({len(items)}):\n\n"
            + "\n".join(daftar_artikel(items)) + "\n")
    keluarkan(f"Prompt PEMBUATAN GAMBAR ({len(items)} artikel)", teks,
              "Salin blok di bawah, tempel ke ChatGPT. Balasannya berupa prompt gambar "
              "siap pakai per artikel — jalankan satu per satu untuk membuat gambarnya, "
              "lalu masukkan hasilnya lewat **Tulis Manual** di POS. Periksa dulu "
              "anatominya (jumlah jari, bentuk telinga) sebelum dipakai.")


def do_apply():
    if not PAYLOAD.strip():
        sys.exit("PAYLOAD kosong — tempel JSON balasan ChatGPT.")
    teks = PAYLOAD.strip()
    # ChatGPT kerap membungkus balasan dengan ```json meski diminta tidak.
    teks = re.sub(r"^```(?:json)?\s*", "", teks)
    teks = re.sub(r"\s*```$", "", teks).strip()
    try:
        data = json.loads(teks)
    except json.JSONDecodeError as e:
        sys.exit(f"PAYLOAD bukan JSON yang sah: {e}")
    if isinstance(data, dict):
        data = data.get("items") or data.get("data") or [data]
    if not isinstance(data, list):
        sys.exit("PAYLOAD harus berupa array JSON.")

    # Peta slug -> path, supaya slug karangan ditolak alih-alih merusak artikel lain.
    known = {p.stem: p for p in g.CONTENT.glob("*/*.md") if p.stem != "_index"}

    ok = 0
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            print(f"  [LEWAT] elemen #{i}: bukan objek")
            continue
        slug = str(item.get("slug") or "").strip()
        p = known.get(slug)
        if not p:
            print(f"  [LEWAT] elemen #{i}: slug '{slug}' tidak dikenal")
            continue
        text = p.read_text(encoding="utf-8")
        m = FM_RE.search(text)
        if not m:
            print(f"  [LEWAT] {slug}: front matter tak dikenali")
            continue
        fm = m.group(2)
        if HAS_QUERY_RE.search(fm):
            print(f"  [LEWAT] {slug}: sudah punya image_query")
            continue

        animals = [a.lower() for a in list_field("hewan", fm)] or ["kucing"]
        animal_en = g.ANIMAL_EN.get(animals[0], animals[0])
        q1 = anchor(item.get("image_query"), animal_en)
        q2 = anchor(item.get("image_query_fallback"), animal_en)
        if not q1:
            print(f"  [LEWAT] {slug}: image_query kosong")
            continue
        subject = (field("title", fm)
                   if g.HISTORY_SUBCAT in list_field("categories", fm) else "")

        block = (f'image_query = "{esc(q1)}"\n'
                 f'image_query_fallback = "{esc(q2)}"\n'
                 f'image_subject = "{esc(subject)}"\n')
        faq = FAQ_RE.search(fm)
        at = faq.start() if faq else len(fm)
        p.write_text(m.group(1) + fm[:at] + block + fm[at:] + m.group(3) + text[m.end():],
                     encoding="utf-8")
        print(f"  [OK] {slug}\n       query    : {q1}\n       fallback : {q2}")
        ok += 1

    print(f"\nSelesai. {ok} dari {len(data)} entri diterapkan.")
    if not ok:
        print("Tidak ada perubahan.")


if __name__ == "__main__":
    if MODE == "apply":
        do_apply()
    elif MODE == "prompt":
        do_prompt()
    elif MODE in ("prompt-gambar", "gambar"):
        do_prompt_gambar()
    else:
        sys.exit(f"MODE tidak dikenal: '{MODE}' "
                 "(pakai 'prompt', 'apply', atau 'prompt-gambar')")
