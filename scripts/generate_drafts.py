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
  - Gambar: SEMUA kategori utamakan FOTO asli (Pexels); ilustrasi Pixabay
            hanya cadangan terakhir bila Pexels tidak punya hasil.
  - Gemini menulis original, gaya answer-first, + FAQ (dipaksa via schema).
  - Output: file Markdown Hugo (draft=false) -> dijadikan Pull Request utk review.

Env:
  GEMINI_API_KEY  (wajib)
  PEXELS_API_KEY  (opsional) - foto asli utk berita
  PIXABAY_API_KEY (opsional) - ilustrasi/kartun utk non-berita
  NUM_ARTICLES    (opsional) - default 1
  SECTION         (opsional) - paksa kategori tertentu; "auto"/kosong = ikut hari
  GEMINI_MODEL    (opsional) - default gemini-3.5-flash
"""

import os
import re
import io
import sys
import json
import base64
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
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
NUM = int(os.environ.get("NUM_ARTICLES", "1") or "1")
SECTION_OVERRIDE = (os.environ.get("SECTION", "") or "").strip()
MAX_RETRY = 3  # berapa kali coba ulang bila Gemini mengembalikan topik yang sudah ada
# Berapa kandidat foto Pexels diambil saat verifikasi ras aktif. Hasil teratas
# sering salah ras, jadi perlu cadangan untuk dicoba satu per satu.
VERIFY_CANDIDATES = 8

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
    "berita-tren": ["Tren & Lifestyle", "Event & Komunitas", "Ras & Sejarah"],
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
    6: "berita-tren",       # Minggu -> khusus "Ras & Sejarah" (lihat HISTORY_WEEKDAYS)
}

# Hari yang WAJIB mengangkat KUCING. Medsos (IG + Halaman FB) hanya memuat
# artikel kucing & anjing, sedangkan aturan diversifikasi di bawah justru
# mendorong ke hewan lain — tanpa hari khusus ini, medsos nyaris tidak terisi.
# Senin=0 ... Minggu=6.
CAT_WEEKDAYS = {0, 2, 5}    # Senin (Kesehatan), Rabu (Bisnis), Sabtu (Berita & Tren)

# Minggu = slot evergreen "Ras & Sejarah": asal-usul ras kucing/anjing dan kisah
# hewan terkenal (mis. Hachiko). Bukan hari kucing murni — anjing juga boleh,
# dan keduanya sama-sama masuk cakupan medsos.
HISTORY_WEEKDAYS = {6}
HISTORY_SUBCAT = "Ras & Sejarah"

# Nama hewan (slug Indonesia) -> kata kunci Inggris untuk pencarian foto Pexels.
# Dipakai untuk MEWAJIBKAN hewan jadi jangkar query gambar (hindari nyamber foto manusia).
ANIMAL_EN = {
    "kucing": "cat", "anjing": "dog", "kelinci": "rabbit", "hamster": "hamster",
    "burung": "bird", "ikan": "fish", "ikan-hias": "aquarium fish", "ayam": "chicken", "bebek": "duck",
    "kambing": "goat", "sapi": "cattle", "domba": "sheep", "kuda": "horse",
    "kura-kura": "turtle", "marmut": "guinea pig", "ular": "snake", "lebah": "bee",
    "landak": "hedgehog", "sugar-glider": "sugar glider", "iguana": "iguana",
}

# Untuk MENDORONG VARIASI HEWAN di kategori yang mudah jatuh ke "kucing terus"
# (Berita & Tren, Bisnis Hewan). Pets + ternak HALAL (tanpa babi/celeng).
VARIETY_PETS = ["anjing", "kelinci", "hamster", "burung", "ikan hias", "marmut", "kura-kura"]
VARIETY_LIVESTOCK = ["ayam", "bebek", "kambing", "domba", "sapi", "ikan lele",
                     "burung puyuh", "lebah madu"]

WIB = datetime.timezone(datetime.timedelta(hours=7))

SYSTEM = """Kamu penulis konten untuk blog Central Cat's — bisnis grooming, treatment kutu, cat hotel, dan petshop kucing di Tangerang (berdiri 2020). Pembaca adalah pemilik hewan peliharaan, terutama kucing (sering disebut "anabul").

ATURAN WAJIB:
1. Tulis konten 100% ORIGINAL dengan kata-katamu sendiri. JANGAN menyalin atau memparafrase ketat dari sumber mana pun.
2. Bahasa Indonesia yang hangat, ramah, jelas, dan mudah dipahami pemilik kucing awam. Boleh memakai istilah "anabul".
3. AKURAT. JANGAN mengarang statistik, angka, persentase, hasil studi, atau kutipan sumber. Jika tidak yakin pada sebuah fakta, sampaikan secara umum tanpa angka palsu.
4. Untuk topik KESEHATAN: bersifat edukasi umum saja. JANGAN memberi dosis obat spesifik, diagnosis pasti, atau resep medis. WAJIB menyarankan konsultasi ke dokter hewan untuk kondisi yang butuh penanganan, dan akhiri artikel kesehatan dengan kalimat saran konsultasi dokter hewan.
4b. SEBUT NARASUMBER/OTORITAS (memperkuat E-E-A-T): bila relevan, sebutkan NAMA lembaga atau profesi yang menjadi rujukan di dalam kalimat — mis. "dokter hewan", "asosiasi ras kucing CFA", "American Kennel Club (AKC)", "WSAVA (asosiasi dokter hewan hewan kecil sedunia)", "AAFP", "FCI", "Kementerian Pertanian", atau "pengalaman tim groomer Central Cat's". Sebut nama lembaganya saja sebagai pedoman — JANGAN mengarang kutipan langsung, nomor halaman, judul studi, tahun terbit, atau statistik dari lembaga itu. Bila tidak yakin sebuah lembaga benar-benar menyatakan hal tersebut, cukup sampaikan sebagai pengetahuan umum tanpa menyebut lembaga.
5. JANGAN membuat klaim berlebihan atau menyesatkan tentang produk maupun hasil.
6. SEO: judul jelas & menarik (idealnya <= 60 karakter), ringkasan memikat <= 150 karakter, gunakan subjudul (## dan ###) yang terstruktur, dan kata kunci yang muncul natural — TANPA keyword stuffing.
7. Tubuh artikel dalam Markdown, sekitar 600-1000 kata: paragraf pembuka, beberapa subjudul, poin praktis, dan kesimpulan singkat. JANGAN menulis judul utama sebagai H1 (#) di dalam body — judul sudah dipakai terpisah.
8. JAWAB LANGSUNG (penting untuk mesin pencari & asisten AI): paragraf PEMBUKA harus langsung menjawab inti pertanyaan/topik secara ringkas (definisi/jawaban inti dalam 2-3 kalimat pertama), baru diperdalam. Ini membantu artikel dikutip AI seperti ChatGPT, Gemini, dan Google AI Overviews.
9. Bila wajar, rumuskan judul & beberapa subjudul sebagai PERTANYAAN yang benar-benar diketik orang. Gunakan kalimat ringkas & mudah dipindai.
9b. AJAK PEMBACA BERINTERAKSI: tutup artikel dengan 1-2 kalimat hangat berisi PERTANYAAN TERBUKA atau ajakan yang memancing pembaca berbagi pengalaman — mis. "Kalau anabul kamu, cara mana yang paling cocok?" atau "Punya pengalaman serupa? Bagikan cerita kamu." Ajak mereka bercerita lewat Instagram @centralcat_official atau WhatsApp Central Cat's (sebut sebagai TEKS biasa, JANGAN dibuat tautan). CATATAN: blog ini TIDAK punya kolom komentar — JANGAN menulis "tulis di kolom komentar" atau menyuruh pembaca berkomentar di bawah artikel. Untuk artikel kesehatan, taruh ajakan ini SEBELUM kalimat penutup saran konsultasi dokter hewan (aturan 4), jangan menggantikannya.
10. ATURAN HALAL (khusus kategori Bisnis Hewan): topik boleh mencakup hewan peliharaan dan ternak HALAL (mis. ayam, bebek, kambing, sapi, domba, kelinci, ikan, lebah madu). DILARANG KERAS mengangkat konten yang berpusat pada hewan haram dalam Islam (mis. babi/celeng) maupun budidaya/produk turunannya.
11. CAKUPAN HEWAN: kucing adalah TEMA UTAMA blog (mayoritas artikel), tetapi artikel BOLEH membahas hewan peliharaan lain (anjing, kelinci, hamster, burung, ikan, dll) bila relevan & bermanfaat — tidak harus selalu kucing. Sesuaikan isi dengan hewan yang dibahas.
12. TAUTAN KE LAYANAN (internal natural, BUKAN keyword stuffing): bila relevan dengan topik, sisipkan 1 (maksimal 2) tautan Markdown ke layanan Central Cat's di dalam body, HANYA dari daftar URL berikut — JANGAN mengarang URL lain, JANGAN menaut ke blog ini sendiri:
   - Grooming / treatment kutu / cat hotel: https://www.centralcats.id/layanan
   - Booking layanan: https://app.centralcats.id/booking
   - Lokasi & antar-jemput: https://www.centralcats.id/lokasi
   Tempatkan secara WAJAR di tengah atau akhir artikel sebagai ajakan halus (mis. "...bisa dibantu lewat [layanan grooming Central Cat's](https://www.centralcats.id/layanan)..."), TIDAK memaksa dan TIDAK di setiap paragraf. Lewati saja bila benar-benar tidak relevan dengan topik.

Balas HANYA satu objek JSON valid dengan struktur:
{"title": "...", "slug": "...", "subcategory": "...", "tags": ["...","..."], "summary": "...", "image_query": "...", "hewan": ["..."], "body": "...", "faq": [{"q": "...", "a": "..."}]}
- "slug": huruf kecil, kata dipisah tanda hubung, tanpa spasi/tanda baca.
- "subcategory": pilih SATU dari daftar yang diberikan.
- "tags": 2-4 tag relevan (huruf kecil).
- "image_query": 2-4 kata BAHASA INGGRIS untuk mencari FOTO yang BENAR-BENAR SESUAI ISI ARTIKEL — bukan foto hewan generik. WAJIB menyebut BAGIAN TUBUH, OBJEK, atau ADEGAN yang jadi fokus artikel, bukan cuma nama hewannya. Contoh:
    * artikel membersihkan telinga kucing -> "cat ear close up" (BUKAN "cute cat")
    * artikel menyikat gigi kucing -> "cat teeth brushing"
    * artikel kucing di carrier -> "cat inside carrier"
    * artikel memotong kuku -> "cat paw claws"
    * artikel bulu kusut -> "cat fur brushing"
    * artikel kandang kelinci -> "rabbit in cage"
  Selalu sertakan nama hewannya di depan. HINDARI istilah abstrak/medis yang tidak punya stok foto (JANGAN mis. "urinary tract infection", "gastrointestinal stasis", "nutrition deficiency") — terjemahkan jadi adegan yang KELIHATAN (mis. untuk artikel penyakit pencernaan kelinci: "rabbit eating hay").
- "image_query_fallback": 2-3 kata BAHASA INGGRIS, versi LEBIH UMUM dari image_query untuk dipakai bila query spesifik tidak menemukan foto. Tetap relevan & tetap menyebut hewannya (mis. image_query "cat ear close up" -> fallback "cat face close up"; "cat inside carrier" -> "cat travel"). JANGAN sama persis dengan image_query.
- "image_subject": HANYA untuk subkategori "Ras & Sejarah". Isi nama subjek yang WAJIB terlihat di foto, BAHASA INDONESIA, sebut rasnya lengkap (mis. "kucing ras Maine Coon", "anjing ras Akita"). Foto kandidat akan diperiksa ulang terhadap kalimat ini, jadi tulis apa adanya tanpa kata tambahan. Untuk subkategori lain, kosongkan.
- "hewan": 1-2 nama HEWAN UTAMA yang dibahas artikel, huruf kecil & tunggal (mis. ["kucing"], ["anjing"], ["kelinci"], ["ayam"]). Bila artikel umum/tidak spesifik ke satu hewan, pakai ["kucing"] (tema utama blog). JANGAN memasukkan hewan haram (mis. babi/celeng).
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
        "image_query_fallback": {"type": "STRING"},
        "image_subject": {"type": "STRING"},
        "hewan": {"type": "ARRAY", "items": {"type": "STRING"}},
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
    "required": ["title", "slug", "subcategory", "tags", "summary", "image_query",
                 "image_query_fallback", "body", "faq"],
}


def pick_section():
    if SECTION_OVERRIDE and SECTION_OVERRIDE.lower() != "auto":
        if SECTION_OVERRIDE in SECTIONS:
            return SECTION_OVERRIDE
        print(f"(SECTION '{SECTION_OVERRIDE}' tidak dikenal, pakai jadwal hari)", file=sys.stderr)
    today = datetime.datetime.now(WIB).weekday()
    return WEEKDAY_SECTION.get(today)


def is_cat_day():
    """Hari WAJIB kucing (Senin, Rabu, Sabtu) — menjamin pasokan artikel kucing
    untuk auto-post medsos, yang HANYA memuat artikel kucing (lihat Bagian 13).
    Hari lain tetap dipakai untuk diversifikasi hewan demi SEO non-kucing.
    Bisa dipaksa lewat env FORCE_CAT=1 / dimatikan dengan FORCE_CAT=0."""
    force = (os.environ.get("FORCE_CAT", "") or "auto").strip().lower()
    if force in ("1", "true", "yes"):
        return True
    if force in ("0", "false", "no"):
        return False
    return datetime.datetime.now(WIB).weekday() in CAT_WEEKDAYS


def is_history_day():
    """Hari slot evergreen "Ras & Sejarah" (Minggu). Dipaksa lewat FORCE_HISTORY=1."""
    force = (os.environ.get("FORCE_HISTORY", "") or "auto").strip().lower()
    if force in ("1", "true", "yes"):
        return True
    if force in ("0", "false", "no"):
        return False
    return datetime.datetime.now(WIB).weekday() in HISTORY_WEEKDAYS


def slugify(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:80] or "artikel"


def _norm(s):
    """Normalisasi judul untuk pembanding duplikat: huruf kecil, tanpa tanda baca."""
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return " ".join(s.split()).strip()


# Kata yang tidak membawa topik. Dibuang sebelum membandingkan judul supaya
# "Cara ... yang Aman" dan "... dengan Aman" tidak dianggap berbeda hanya karena
# susunan katanya.
STOPWORDS = {
    "cara", "yang", "dengan", "dan", "untuk", "di", "ke", "dari", "pada", "agar",
    "supaya", "tips", "panduan", "apa", "saja", "bagaimana", "kenapa", "mengapa",
    "itu", "ini", "si", "atau", "bisa", "harus", "saat", "ketika", "sebagai",
    "tanpa", "lebih", "paling", "juga", "serta", "adalah", "akan", "dalam",
    "secara", "punya", "milik", "buat", "biar",
}

# Ambang kemiripan judul. DIUKUR, bukan ditebak: dari 88 artikel yang sudah ada,
# pasangan sah yang PALING mirip cuma 0,62 ("Waspada Alergi pada Kucing" vs
# "Waspada Tungau Telinga pada Kucing" — memang dua topik berbeda), sedangkan
# duplikat nyata yang lolos 18 Agu 2026 mencetak 1,00. Jadi 0,75 duduk di jurang
# antara keduanya. Menaikkan ambang = duplikat lolos lagi; menurunkannya sampai
# di bawah 0,62 = topik sah ikut diblokir (dan 3 kali tolak berarti hari itu
# tidak ada artikel sama sekali).
DUP_SIMILARITY = 0.75


def _tokens(title):
    """Himpunan kata bermakna sebuah judul."""
    return {w for w in _norm(title).split() if w and w not in STOPWORDS}


def _similarity(a, b):
    """Jaccard: irisan dibagi gabungan. 1,0 = himpunan katanya persis sama."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def existing_index():
    """Kumpulkan (daftar judul, set slug, set judul ternormalisasi) dari SEMUA
    artikel yang sudah ada — KECUALI _index.md. Dipakai untuk mencegah duplikat
    topik (bandingkan ke seluruh katalog, bukan cuma 40 terakhir)."""
    titles, slugs, norm_titles = [], set(), set()
    if not CONTENT.exists():
        return titles, slugs, norm_titles
    for p in CONTENT.rglob("*.md"):
        if p.name == "_index.md":
            continue
        slugs.add(p.stem.lower())
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r'title\s*=\s*"([^"]+)"', txt) or re.search(r'^title:\s*"?([^"\n]+)"?', txt, re.M)
        if m:
            t = m.group(1).strip()
            titles.append(t)
            norm_titles.add(_norm(t))
    return titles, slugs, norm_titles


def section_hewan_counts(section):
    """Hitung berapa artikel per hewan dalam satu kategori (untuk dorong variasi)."""
    counts = {}
    d = CONTENT / section
    if not d.exists():
        return counts
    for p in d.glob("*.md"):
        if p.name == "_index.md":
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        m = re.search(r"hewan\s*=\s*\[([^\]]*)\]", txt)
        if m:
            for h in re.findall(r'"([^"]+)"', m.group(1)):
                counts[h] = counts.get(h, 0) + 1
    return counts


def is_duplicate(data, slugs, norm_titles, titles=()):
    """True bila artikel ini mengulang topik yang sudah ada di katalog.

    Perbandingan PERSIS saja tidak cukup, dan itu terbukti: 18 Agu 2026 lolos
    "Cara Memandikan Hamster dengan Pasir Mandi yang Aman" padahal katalog sudah
    memuat "Cara Aman Memandikan Hamster dengan Mandi Pasir" — beda urutan kata,
    string-nya jelas tidak sama, topiknya sama persis. Model bahkan SUDAH diberi
    tahu lewat daftar HINDARI di prompt dan tetap mengulang; jadi yang harus
    menangkap adalah penjaga ini, bukan modelnya.
    """
    slug = slugify(data.get("slug") or data.get("title") or "")
    if slug in slugs:
        return True, f"slug '{slug}' sudah ada"
    nt = _norm(data.get("title", ""))
    if nt and nt in norm_titles:
        return True, f"judul '{data.get('title')}' mirip artikel yang sudah ada"

    judul = data.get("title", "")
    toks = _tokens(judul)
    if toks:
        mirip = max(
            ((_similarity(toks, _tokens(t)), t) for t in titles if t),
            default=(0.0, ""),
        )
        if mirip[0] >= DUP_SIMILARITY:
            return True, (f"judul '{judul}' {mirip[0]:.0%} sama topiknya dengan "
                          f"'{mirip[1]}'")
    return False, ""


def gemini_article(section, avoid):
    subcats = SUBCATS[section]
    # SELURUH judul dikirim, tanpa dipotong. Dulu `avoid[-80:]` — dan karena
    # existing_index() menelusuri direktori (bukan urutan terbit), "80 terakhir"
    # berarti 80 yang kebetulan terbaca belakangan: begitu katalog lewat 80
    # artikel, sebagian judul berhenti diberitahukan ke model TANPA pola apa pun.
    # 88 judul ~ 1 rb token; kalaupun kelak jadi 500, itu masih murah dibanding
    # menerbitkan artikel yang mengulang topik.
    avoid_txt = "; ".join(t for t in avoid if t) if avoid else "(belum ada)"
    extra = ""
    if section == "bisnis-hewan":
        extra += ("Topik boleh bisnis hewan peliharaan ATAU ternak HALAL "
                  "(ayam, kambing, sapi, domba, kelinci, ikan, dll). DILARANG babi/hewan haram.\n")

    # MINGGU: slot evergreen "Ras & Sejarah" — subkategori dikunci, bukan dipilih
    # Gemini, agar slot ini benar-benar terisi tiap minggu.
    history_day = is_history_day() and HISTORY_SUBCAT in SUBCATS[section]
    if history_day:
        subcats = [HISTORY_SUBCAT]
        extra += (f"HARI KHUSUS EVERGREEN — WAJIB pakai subkategori "
                  f"\"{HISTORY_SUBCAT}\". Jangan pilih subkategori lain.\n")

    # HARI KUCING: pasokan wajib untuk auto-post medsos. Semua aturan
    # diversifikasi hewan di bawah dimatikan agar tidak saling bertentangan.
    cat_day = is_cat_day() and not history_day
    if cat_day:
        extra += ("HARI KHUSUS KUCING — artikel ini WAJIB tentang KUCING. "
                  "Set field \"hewan\" ke [\"kucing\"]. Pilih sudut yang segar dan "
                  "belum dibahas; jangan mengulang topik kucing yang sudah ada.\n")
        if section == "bisnis-hewan":
            extra += ("Karena kategorinya Bisnis Hewan, angkat sisi USAHA yang "
                      "berhubungan dengan kucing (mis. petshop, jasa grooming, "
                      "cat hotel/penitipan, pakan & aksesori kucing, breeding "
                      "beretika) — bukan ternak.\n")

    # Dorong VARIASI HEWAN untuk kategori yang mudah jatuh ke "kucing terus".
    # Berita & Tren + Bisnis Hewan boleh mengangkat hewan peliharaan lain atau ternak halal.
    if not cat_day and not history_day and section in ("berita-tren", "bisnis-hewan"):
        counts = section_hewan_counts(section)
        total = sum(counts.values())
        cat = counts.get("kucing", 0)
        pool = ", ".join(VARIETY_PETS + VARIETY_LIVESTOCK)
        # Subkategori "Ras & Sejarah" (khusus berita-tren) SENGAJA dikecualikan
        # dari aturan anti-dominasi kucing: itu jalur evergreen kucing yang memasok
        # konten untuk auto-post medsos (medsos hanya memuat artikel kucing).
        kecuali = ("" if section != "berita-tren" else
                   " KECUALI bila kamu memilih subkategori \"Ras & Sejarah\","
                   " yang memang khusus kucing/anjing dan tetap boleh dipilih.")
        if total >= 3 and cat >= total * 0.5:
            extra += ("PENTING — kategori ini SUDAH kebanyakan artikel tentang kucing. "
                      "Kali ini JANGAN pilih kucing. WAJIB angkat hewan peliharaan lain "
                      f"atau ternak halal, mis.: {pool}. Set field \"hewan\" ke hewan itu "
                      f"(bukan kucing).{kecuali}\n")
        else:
            extra += ("Variasikan hewan yang dibahas — TIDAK harus kucing. Boleh hewan "
                      f"peliharaan lain atau ternak halal ({pool}).\n")

    # Diversifikasi hewan untuk kategori PERAWATAN (Kesehatan & Panduan): kucing
    # tetap tema utama, tetapi bila sudah terlalu dominan (>65%) WAJIB angkat hewan
    # peliharaan LAIN — agar blog menjangkau kata kunci non-kucing yang saingannya
    # lebih sepi (ternak halal TIDAK dipakai di sini, hanya untuk Bisnis Hewan).
    if not cat_day and section in ("kesehatan-hewan", "panduan-tips"):
        counts = section_hewan_counts(section)
        total = sum(counts.values())
        cat = counts.get("kucing", 0)
        pool = ", ".join(VARIETY_PETS)
        if total >= 3 and cat >= total * 0.65:
            extra += ("PENTING — kategori ini SUDAH didominasi artikel tentang kucing. "
                      "Kali ini JANGAN pilih kucing. WAJIB angkat HEWAN PELIHARAAN lain "
                      f"(mis.: {pool}). Set field \"hewan\" ke hewan itu (bukan kucing). "
                      "Bila artikel bukan tentang kucing, JANGAN memakai subkategori khusus "
                      "kucing seperti \"Kesehatan Kucing\".\n")
        # Bila kucing belum dominan, biarkan default (kucing sebagai tema utama blog).
    if section == "berita-tren":
        extra += ("Jika berita/tren ini juga menyangkut PELUANG USAHA/BISNIS, tambahkan tag "
                  "\"bisnis\" pada field tags agar mudah ditemukan lintas-topik.\n")
        extra += (
            "Subkategori \"Ras & Sejarah\" dipakai untuk artikel SEJARAH & ASAL-USUL "
            "RAS KUCING/ANJING DUNIA, atau KISAH HEWAN TERKENAL. Contoh sudut:\n"
            "- Ras kucing: Persia, Maine Coon, Anggora Turki, Siam, Sphynx, Bengal, "
            "Norwegian Forest, kucing kampung/domestik Nusantara.\n"
            "- Ras anjing: Golden Retriever, Akita, Shiba Inu, German Shepherd, "
            "Poodle, Kintamani (ras asli Indonesia).\n"
            "- Kisah hewan terkenal: mis. Hachiko (Akita yang menunggu majikannya di "
            "Stasiun Shibuya), Balto, atau kucing/anjing bersejarah lain.\n"
            "Bahas asal-usulnya, bagaimana berkembang, ciri khas fisik & sifatnya, "
            "serta perannya dalam budaya. Artikel subkategori ini WAJIB tentang KUCING "
            "atau ANJING — set \"hewan\" ke [\"kucing\"] atau [\"anjing\"] sesuai isi. "
            "Tetap faktual; jangan mengarang klaim sejarah.\n"
            "Berpedomanlah pada organisasi ras yang diakui dan sebut namanya di dalam "
            "artikel sebagai rujukan (mis. \"menurut CFA\"): untuk KUCING — CFA (Cat "
            "Fanciers' Association, cfa.org), TICA, atau FIFe; untuk ANJING — AKC "
            "(American Kennel Club, akc.org) atau FCI (Federation Cynologique "
            "Internationale). Untuk sisi sejarah/budaya boleh merujuk museum atau "
            "lembaga resmi setempat. INGAT aturan 1 & 3: tulis ulang dengan "
            "kata-katamu sendiri, JANGAN menyalin teks mereka, dan JANGAN mengarang "
            "tahun/angka bila tidak yakin — cukup sampaikan secara umum.\n")
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


def verify_photo(img_bytes, subject):
    """Tanya Gemini (vision): apakah foto ini BENAR-BENAR menampilkan `subject`?

    Ada karena pencarian kata kunci Pexels TIDAK memahami ras: query
    "cat maine coon" bisa mengembalikan kucing berbulu panjang mana saja
    (Siberian, Norwegian Forest, domestik) karena penandaan foto stok dibuat
    pengunggah, bukan juri ras. Untuk artikel slot "Ras & Sejarah" itu bukan
    sekadar foto kurang nyambung — artikelnya jadi SALAH secara faktual.

    Sengaja FAIL-CLOSED: ragu, ciri ras tak terlihat, atau API error = TOLAK.
    Artikel tanpa foto jauh lebih baik daripada artikel ras berfoto ras lain.
    """
    prompt = (
        f"Apakah foto ini menampilkan {subject}?\n"
        "Jawab HANYA satu kata: YA atau TIDAK.\n"
        "Jawab TIDAK bila kamu ragu, bila hewan di foto tampak dari ras lain, "
        "bila ciri khas ras tidak terlihat jelas, atau bila tidak ada hewan "
        "yang dimaksud di foto."
    )
    try:
        r = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [
                    {"inline_data": {"mime_type": "image/jpeg",
                                     "data": base64.b64encode(img_bytes).decode("ascii")}},
                    {"text": prompt},
                ]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 512},
            },
            timeout=90,
        )
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"].get("parts") or []
        answer = " ".join(p.get("text", "") for p in parts).strip().upper()
    except Exception as e:
        print(f"    (verifikasi foto gagal, foto ditolak: {e})", file=sys.stderr)
        return False
    ok = answer.startswith("YA")
    if not ok:
        print(f"    (foto ditolak verifikasi: jawaban \"{answer[:40]}\")", file=sys.stderr)
    return ok


def fetch_photo_pexels(query, slug, subject=None, candidates=1):
    """Ambil foto dari Pexels. Bila `subject` diisi, tiap kandidat diverifikasi
    lewat `verify_photo()` dan yang tidak lolos dilewati — makanya `candidates`
    (per_page) dinaikkan saat verifikasi aktif, agar ada cadangan untuk dicoba."""
    if not PEXELS_KEY or not query:
        return None, None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params={"query": query, "per_page": max(1, candidates),
                    "orientation": "landscape"},
            timeout=60,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        for p in photos:
            src = p["src"].get("large2x") or p["src"].get("large") or p["src"]["original"]
            img = requests.get(src, timeout=60).content
            if subject and not verify_photo(img, subject):
                continue
            return _save_webp(img, slug), f"Foto: {p.get('photographer', 'Pexels')} / Pexels"
        return None, None
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


def fetch_image(queries, slug, subject=None, strict=False):
    """Semua kategori: UTAMAKAN FOTO ASLI (Pexels). Ilustrasi Pixabay hanya
    dipakai sebagai cadangan terakhir bila Pexels tidak punya hasil, supaya
    setiap artikel tetap punya gambar yang relevan & profesional.

    `queries` = daftar kata kunci dari yang PALING SPESIFIK ke paling umum
    (mis. "cat ear cleaning" -> "cat ear close up" -> "cat"). Query spesifik
    dicoba dulu agar foto benar-benar sesuai isi artikel; kalau stok fotonya
    tidak ada, baru melebar — supaya artikel tetap dapat FOTO, bukan langsung
    jatuh ke ilustrasi kartun.

    `subject` = subjek yang WAJIB terlihat (mis. "kucing ras Maine Coon");
    bila diisi, tiap kandidat foto diverifikasi Gemini vision.
    `strict`  = artikel ras: lebih baik TANPA gambar daripada salah ras, jadi
    ilustrasi Pixabay pun tidak dipakai sebagai pelarian."""
    seen = []
    for q in queries:
        q = (q or "").strip()
        if not q or q.lower() in seen:
            continue
        seen.append(q.lower())
        path, credit = fetch_photo_pexels(
            q, slug, subject=subject, candidates=VERIFY_CANDIDATES if subject else 1)
        if path:
            print(f"  Foto ketemu dgn query: \"{q}\"", file=sys.stderr)
            return path, credit
    if strict:
        # Ilustrasi kartun juga tidak bisa menjamin rasnya benar — lebih baik kosong.
        print("  (artikel ras: tak ada foto yang lolos verifikasi -> TANPA gambar)",
              file=sys.stderr)
        return None, None
    # Semua query gagal di Pexels -> ilustrasi (cadangan terakhir).
    for q in queries:
        if not (q or "").strip():
            continue
        path, credit = fetch_illustration_pixabay(q.strip(), slug)
        if path:
            print(f"  (jatuh ke ilustrasi Pixabay, query: \"{q}\")", file=sys.stderr)
            return path, credit
    return None, None


def fetch_photos_bytes(queries, subject=None, count=4, per_query=12):
    """Ambil hingga `count` foto BERBEDA dari Pexels sebagai bytes mentah.

    Dipakai carousel medsos (scripts/post_instagram.py). Beda dari `fetch_image()`
    yang mengembalikan SATU path `.webp` di `static/images/`: di sini foto tidak
    disimpan ke repo sama sekali — bytes-nya langsung dikonversi JPEG lalu
    dititipkan sebagai asset release `ig-images`. Alasannya foto carousel hanya
    dipakai medsos, tidak pernah tampil di blog, jadi tak ada gunanya menambah
    3-4 biner per artikel ke histori git (lihat CLAUDE.md Bagian 8a).

    `queries` bertingkat dari PALING SPESIFIK ke paling umum, sama seperti
    `fetch_image()`. `subject` mengaktifkan verifikasi Gemini vision untuk SETIAP
    kandidat — ini yang menjamin foto carousel benar-benar berkaitan dengan isi
    artikel, bukan sekadar hewan yang sama. Foto yang tidak lolos dibuang, dan
    lebih baik pulang dengan sedikit foto daripada memaksa penuh dengan foto
    yang tidak nyambung.
    """
    out, seen_ids, seen_q = [], set(), set()
    if not PEXELS_KEY:
        return out
    for q in queries:
        q = (q or "").strip()
        if not q or q.lower() in seen_q:
            continue
        seen_q.add(q.lower())
        if len(out) >= count:
            break
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": q, "per_page": per_query, "orientation": "landscape"},
                timeout=60,
            )
            r.raise_for_status()
            photos = r.json().get("photos", [])
        except Exception as e:
            print(f"  (Pexels dilewati utk \"{q}\": {e})", file=sys.stderr)
            continue
        for p in photos:
            if len(out) >= count:
                break
            pid = p.get("id")
            if pid in seen_ids:
                continue
            src = p["src"].get("large2x") or p["src"].get("large") or p["src"]["original"]
            try:
                img = requests.get(src, timeout=60).content
            except Exception:
                continue
            if subject and not verify_photo(img, subject):
                continue
            seen_ids.add(pid)
            out.append({
                "bytes": img,
                "credit": f"Foto: {p.get('photographer', 'Pexels')} / Pexels",
                "query": q,
            })
    return out


def fix_escapes(s):
    """Gemini kadang men-DOUBLE-escape newline/tab di dalam string JSON
    (mis. menulis "\\n\\n"), sehingga setelah json.loads tersisa literal
    backslash-n — bukan baris baru asli — dan Markdown jadi satu paragraf
    gepeng. Normalkan urutan escape umum ke karakter aslinya. Aman untuk
    teks Indonesia (hanya menyentuh \\n, \\r, \\t; tak menyentuh unicode)."""
    if not s:
        return s
    return (s.replace("\\r\\n", "\n")
             .replace("\\n", "\n")
             .replace("\\r", "\n")
             .replace("\\t", "\t"))


def write_article(section, data):
    title = (data.get("title") or "Artikel Tanpa Judul").strip()
    slug = slugify(data.get("slug") or title)
    path = CONTENT / section / f"{slug}.md"
    if path.exists():
        # Tak seharusnya terjadi (sudah dicek is_duplicate). Jangan buat file kembar
        # bertimestamp — lempar error agar artikel ini DILEWATI, bukan jadi duplikat.
        raise FileExistsError(f"slug '{slug}' sudah ada — batal menulis duplikat")

    now = datetime.datetime.now(WIB)
    date_str = now.strftime("%Y-%m-%dT%H:%M:%S") + "+07:00"
    sub = (data.get("subcategory") or "").strip()
    tags = data.get("tags") or []
    tags_toml = ", ".join('"{}"'.format(str(t).replace('"', "")) for t in tags)

    # taxonomy "hewan": normalisasi ke slug huruf kecil, default ["kucing"], jaga aturan halal
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

    # Gambar: WAJIB jangkar HEWAN utama (Inggris) di query agar foto Pexels relevan
    # & tidak nyamber subjek manusia. Bila Gemini sudah menyebut hewannya, query dipakai apa adanya.
    animal_en = ANIMAL_EN.get(hewan_list[0], hewan_list[0])

    def _anchor(q):
        q = (q or "").strip()
        if not q:
            return ""
        if re.search(r"\b" + re.escape(animal_en) + r"\b", q.lower()):
            return q
        return (animal_en + " " + q).strip()

    # Bertingkat dari PALING SPESIFIK ke paling umum: query fokus (mis. "cat ear
    # close up") -> fallback lebih luas -> nama hewan saja. Tujuannya foto benar-
    # benar sesuai isi artikel, tapi artikel tetap dapat FOTO kalau stok query
    # spesifik kosong (daripada langsung jatuh ke ilustrasi kartun).
    queries = [
        _anchor(data.get("image_query")),
        _anchor(data.get("image_query_fallback")),
        animal_en,
    ]

    # Artikel RAS (slot "Ras & Sejarah"): fotonya WAJIB ras yang dibahas.
    # Fallback terakhir `animal_en` ("cat") DIBUANG — kalau tidak, artikel
    # "Sejarah Maine Coon" bisa tampil dengan kucing sembarangan, dan itu
    # kesalahan faktual, bukan sekadar foto kurang nyambung.
    is_breed = sub == HISTORY_SUBCAT
    subject = ""
    if is_breed:
        queries = queries[:2]
        subject = (data.get("image_subject") or "").strip() or data.get("title", "")

    queries = [q for q in queries if q]
    print(f"  Query gambar (spesifik -> umum): {queries} (hewan: {hewan_list[0]})",
          file=sys.stderr)
    if subject:
        print(f"  Verifikasi ras aktif — subjek wajib: \"{subject}\"", file=sys.stderr)
    img_path, credit = fetch_image(queries, slug, subject=subject or None, strict=is_breed)
    if credit:
        print(f"  {credit}", file=sys.stderr)

    summary = (data.get("summary") or "").replace('"', "'").strip()
    title_esc = title.replace('"', "'")
    body = fix_escapes(data.get("body") or "").strip()
    images_toml = f'"{img_path}"' if img_path else ""

    def _q_esc(s):
        return " ".join(str(s or "").split()).replace('"', "'").strip()

    def _clean(s):
        # buang escape literal (mis. "\n") jadi spasi agar FAQ 1-baris tetap rapi
        s = str(s).replace("\\r\\n", " ").replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
        return " ".join(s.split()).replace('"', "'").strip()
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
        # Query gambar DISIMPAN supaya carousel medsos (post_instagram.py) bisa
        # mencari foto tambahan dengan kata kunci spesifik yang SAMA — bukan
        # menebak ulang dari judul. Tanpa ini, foto ke-2 dst gampang melenceng
        # jadi hewan generik. Tidak dipakai template Hugo mana pun.
        f'image_query = "{_q_esc(queries[0] if queries else "")}"\n'
        f'image_query_fallback = "{_q_esc(queries[1] if len(queries) > 1 else "")}"\n'
        f'image_subject = "{_q_esc(subject)}"\n'
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

    avoid, slugs, norm_titles = existing_index()
    created = []
    for i in range(max(1, NUM)):
        data = None
        for attempt in range(1, MAX_RETRY + 1):
            try:
                d = gemini_article(section, avoid)
            except Exception as e:
                print(f"[GAGAL] artikel ke-{i+1} (percobaan {attempt}): {e}", file=sys.stderr)
                continue
            dup, why = is_duplicate(d, slugs, norm_titles, avoid)
            if not dup:
                data = d
                break
            print(f"  (percobaan {attempt}: DUPLIKAT — {why}; regenerasi)", file=sys.stderr)
            avoid.append(d.get("title", ""))  # supaya percobaan berikutnya menghindarinya
        if not data:
            print(f"[GAGAL] artikel ke-{i+1}: tetap duplikat setelah {MAX_RETRY} percobaan — dilewati.",
                  file=sys.stderr)
            continue
        try:
            p, has_img = write_article(section, data)
        except Exception as e:
            print(f"[GAGAL] artikel ke-{i+1}: {e}", file=sys.stderr)
            continue
        # Perbarui indeks in-run agar artikel di run yang sama tak saling menduplikasi.
        avoid.append(data.get("title", ""))
        slugs.add(p.stem.lower())
        norm_titles.add(_norm(data.get("title", "")))
        mark = "[img]" if has_img else "[teks]"
        created.append(str(p.relative_to(ROOT)))
        print(f"[OK] {mark} {p.relative_to(ROOT)}")

    if not created:
        sys.exit("Tidak ada artikel yang berhasil dibuat.")
    print("\nArtikel dibuat (menunggu review lewat Pull Request):")
    for c in created:
        print("  -", c)


if __name__ == "__main__":
    main()
