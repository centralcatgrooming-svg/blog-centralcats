#!/usr/bin/env python3
"""Auto-posting Instagram untuk ARTIKEL BARU (Instagram Graph API - Content Publishing).

Dipanggil oleh .github/workflows/post-instagram.yml saat ada file artikel baru
(ditambahkan) di push ke main -- pola deteksi sama dengan notifikasi OneSignal.

Alur per artikel:
  1. Baca front matter (title / summary / images / tags / hewan).
  2. Ambil gambar unggulan (lokal `static/<images[0]>`, fallback unduh dari BASE_URL)
     lalu konversi ke **JPEG 1080x1080** (center crop).
     -> Instagram HANYA menerima JPEG; gambar blog kita semuanya .webp, jadi
        konversi ini WAJIB. Rasio 1:1 juga menjamin lolos syarat rasio IG
        (4:5 s/d 1.91:1).
  3. Unggah JPEG sebagai **GitHub Release asset** (tag `ig-images`) -> dapat URL
     publik permanen tanpa menambah biner ke histori git repo (lihat CLAUDE.md 8a).
     Ini juga menghindari balapan dengan deploy GitHub Pages (gambar di
     blog.centralcats.id baru hidup setelah build Hugo selesai).
  4. Publish 2 langkah: POST /{ig-user-id}/media -> POST /{ig-user-id}/media_publish.

NON-BLOCKING: skrip ini tidak boleh menggagalkan job. Token kosong/kedaluwarsa,
gambar tidak ada, atau API error -> hanya ::notice:: / ::warning::, exit 0.

Env:
  IG_USER_ID          Instagram Business Account ID (GitHub Secret).
  IG_ACCESS_TOKEN     Page access token permanen (GitHub Secret). RAHASIA.
  IG_GRAPH_VERSION    Versi Graph API, default "v21.0". Naikkan bila Meta
                      men-sunset versi lama (error "Unsupported get request").
  NEW_FILES           Daftar path artikel baru (1 per baris), dari git diff.
  BASE_URL            mis. "https://blog.centralcats.id/".
  GITHUB_REPOSITORY   "owner/repo" (otomatis di Actions).
  GITHUB_TOKEN        Token Actions dengan permission `contents: write`.
"""
import io
import os
import re
import sys
import json
import time
import pathlib
import urllib.parse
import urllib.request
import urllib.error

try:
    from PIL import Image
    HAS_PIL = True
except Exception:  # pragma: no cover - hanya bila pillow tak terpasang
    HAS_PIL = False

IG_USER_ID = (os.environ.get("IG_USER_ID") or "").strip()
IG_TOKEN = (os.environ.get("IG_ACCESS_TOKEN") or "").strip()
FB_PAGE_ID = (os.environ.get("FB_PAGE_ID") or "").strip()  # kosong = lewati Halaman FB
# Hewan yang boleh masuk medsos (blog tetap SEMUA hewan — kriterianya sengaja beda).
# Kosongkan (SOCIAL_ANIMALS="") untuk mematikan filter & posting semua artikel.
SOCIAL_ANIMALS = [a.strip().lower() for a in
                  (os.environ.get("SOCIAL_ANIMALS", "kucing,anjing")).split(",") if a.strip()]
GRAPH_VERSION = (os.environ.get("IG_GRAPH_VERSION") or "v21.0").strip()
BASE_URL = ((os.environ.get("BASE_URL") or "https://blog.centralcats.id/").strip().rstrip("/")) + "/"
FILES = [f.strip() for f in (os.environ.get("NEW_FILES") or "").splitlines() if f.strip()]

GH_REPO = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
GH_TOKEN = (os.environ.get("GITHUB_TOKEN") or "").strip()
RELEASE_TAG = "ig-images"

# Mode PRATINJAU: hitung caption + gambar 1:1 persis seperti saat posting, unggah
# hasilnya sebagai `preview-<slug>.json` di release `ig-images`, lalu BERHENTI
# sebelum memanggil Graph API. Dipakai POS (Pusat Konten) untuk menampilkan apa
# yang akan tayang supaya bisa ditinjau dulu. Alasan mode ini ada: caption IG
# TIDAK bisa diedit lewat API setelah tayang (lihat CLAUDE.md Bagian 13), jadi
# koreksi setelah posting berarti hapus + posting ulang manual.
DRY_RUN = (os.environ.get("DRY_RUN") or "").strip().lower() in ("1", "true", "yes")

# Jumlah gambar per postingan (1 = perilaku lama, tanpa carousel). Batas keras IG
# adalah 10; default 4 dipilih supaya carousel tetap padat tanpa memaksa foto stok
# yang makin melenceng — kandidat relevan biasanya menipis setelah 3-4 foto.
try:
    CAROUSEL_MAX = max(1, min(10, int(os.environ.get("CAROUSEL_MAX") or 4)))
except ValueError:
    CAROUSEL_MAX = 4

# Daftar pratinjau yang terbentuk, dibaca notify_social_email.py di langkah berikutnya.
SUMMARY_FILE = (os.environ.get("PREVIEW_SUMMARY") or "preview-summary.json").strip()

GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
FM_RE = re.compile(r'^\+\+\+\s*\n(.*?)\n\+\+\+\s*$', re.S | re.M)
MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]*\)')
HEAD_RE = re.compile(r'(?m)^(#{2,3})\s+(.+?)\s*$')

# Hashtag tetap milik brand. Sisanya diturunkan dari `tags`/`hewan` artikel.
BRAND_TAGS = ["centralcats", "groomingkucing", "petshoptangerang", "pasarkemis", "rajeg"]

# Ajakan berkomentar — ditaruh di caption medsos (blog tidak punya kolom komentar).
# Dipilih deterministik dari slug supaya tiap artikel dapat variasi tetapi
# posting ulang artikel yang sama menghasilkan caption yang sama.
ENGAGE = [
    "{H} kamu pernah mengalami ini juga? Cerita dong di kolom komentar \U0001f447",
    "Kalau versi kamu, cara mana yang paling ampuh? Tulis di komentar ya \U0001f447",
    "Masih ada yang mau ditanyakan soal ini? Tulis di kolom komentar, "
    "nanti kami bantu jawab \U0001f447",
    "Menurut kamu poin mana yang paling penting? Bagikan pengalamanmu "
    "di kolom komentar \U0001f447",
    "Sudah pernah coba yang mana? Ceritakan di kolom komentar \U0001f447",
]
MAX_HASHTAGS = 20
MAX_CAPTION = 2200  # batas keras Instagram


# --------------------------------------------------------------------------- utils
def warn(msg):
    print(f"::warning::Instagram: {msg}")


def notice(msg):
    print(f"::notice::Instagram: {msg}")


def http_json(url, data=None, headers=None, method=None, timeout=60):
    """Request JSON. Return (status, dict-atau-teks). Tidak melempar pada HTTPError."""
    body = None
    hdrs = dict(headers or {})
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


# --------------------------------------------------------------- front matter
def split_doc(text):
    """Pisahkan dokumen jadi (front matter, isi artikel)."""
    m = FM_RE.search(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def field(name, fm):
    m = re.search(r'(?m)^\s*%s\s*=\s*"(.*?)"' % re.escape(name), fm)
    return m.group(1) if m else ""


def first_image(fm):
    m = re.search(r'(?m)^\s*images\s*=\s*\[\s*"([^"]+)"', fm)
    return m.group(1) if m else ""


def list_field(name, fm):
    """Ambil isi array TOML sederhana: nama = ["a", "b"] -> ["a", "b"]."""
    m = re.search(r'(?m)^\s*%s\s*=\s*\[(.*?)\]' % re.escape(name), fm, re.S)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def article_url(path):
    """content/<section>/<slug>.md -> BASE/<section>/<slug>/"""
    p = pathlib.PurePosixPath(path.replace("\\", "/"))
    return BASE_URL + p.parts[-2] + "/" + p.stem + "/"


# ------------------------------------------------------------------- caption
def hashtags(fm):
    raw = list_field("tags", fm) + list_field("hewan", fm) + BRAND_TAGS
    out = []
    for t in raw:
        tag = re.sub(r"[^0-9a-z]", "", t.lower())
        if tag and not tag[0].isdigit() and tag not in out:
            out.append(tag)
    return " ".join("#" + t for t in out[:MAX_HASHTAGS])


def plain(s):
    """Buang markup markdown ringan agar enak dibaca di caption IG."""
    s = MD_LINK_RE.sub(r"\1", s)          # [teks](url) -> teks
    s = re.sub(r"[*_`]+", "", s)
    return " ".join(s.split())


def lede(body, min_len=200):
    """Paragraf pembuka artikel (gaya answer-first). Ambil paragraf kedua bila
    yang pertama terlalu pendek, supaya caption tidak terasa nanggung."""
    paras = []
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        # Lewati heading, gambar, shortcode, kutipan, pemisah, dan kredit foto.
        if (not b or b[0] in "#>!-|" or b.startswith("{{")
                or b.lower().startswith("*foto")):
            continue
        paras.append(plain(b))
        if sum(len(p) for p in paras) >= min_len or len(paras) >= 2:
            break
    return "\n\n".join(paras)


def outline(body, limit=5):
    """Daftar isi ringkas dari heading artikel. Utamakan H3 bila artikel punya
    langkah bernomor (lebih konkret), selain itu pakai H2."""
    h2, h3 = [], []
    for hashes, text in HEAD_RE.findall(body):
        t = re.sub(r"^\d+[.)]\s*", "", plain(text))
        (h2 if len(hashes) == 2 else h3).append(t)
    items = h3 if len(h3) >= 3 else h2
    return items[:limit]


def engage(fm, seed):
    """Kalimat ajakan berkomentar, dipilih deterministik dari seed (slug)."""
    animals = [a.lower() for a in list_field("hewan", fm)] or ["kucing"]
    hewan = "Anjing" if animals[0] == "anjing" else (
        "Kucing" if animals[0] == "kucing" else "Anabul")
    idx = sum(ord(c) for c in seed) % len(ENGAGE)
    return ENGAGE[idx].format(H=hewan)


def build_caption(title, fm, body, url=None, seed=""):
    """Caption medsos.

    `summary` di front matter sengaja dibatasi ~155 karakter untuk meta
    description SEO, jadi terlalu pendek untuk medsos. Caption ini memakai
    paragraf pembuka artikel + daftar isi, dengan summary sbg cadangan.

    `url` diisi HANYA untuk Facebook — di sana tautan bisa diklik. Di Instagram
    tautan dalam caption TIDAK bisa diklik, jadi diarahkan ke bio.
    """
    head = [title]
    lead = lede(body) or field("summary", fm)
    if lead:
        head.append(lead)
    items = outline(body)
    if items:
        head.append("Yang dibahas:\n" + "\n".join("• " + i for i in items))

    cta = (f"Baca artikel lengkapnya:\n{url}" if url
           else "Baca artikel lengkapnya di blog kami — tautan ada di bio \U0001f517")
    # Ajakan komentar ikut di ekor agar TIDAK pernah kena pemotongan caption.
    tail = [engage(fm, seed or title),
            cta + "\nCentral Cat's — grooming, petshop & cat hotel di Pasar Kemis & Rajeg."]
    tags = hashtags(fm)
    if tags:
        tail.append(tags)
    tail = "\n\n".join(tail)

    # Potong bagian isi, JANGAN ekornya — CTA & hashtag harus selalu ikut.
    body_text = "\n\n".join(head)
    budget = MAX_CAPTION - len(tail) - 2
    if len(body_text) > budget:
        body_text = body_text[:budget - 1].rstrip() + "…"
    return body_text + "\n\n" + tail


# --------------------------------------------------------------------- gambar
def load_image_bytes(img_path):
    """Ambil biner gambar: utamakan file lokal di checkout, fallback unduh dari situs."""
    if not img_path:
        return None
    local = pathlib.Path("static") / img_path.lstrip("/")
    if local.exists():
        return local.read_bytes()
    url = img_path if img_path.startswith("http") else BASE_URL + img_path.lstrip("/")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read()
    except Exception as e:
        warn(f"gagal mengambil gambar {url}: {e}")
        return None


def to_square_jpeg(img_bytes, size=1080):
    """Konversi ke JPEG persegi {size}x{size} (center crop). Instagram hanya terima JPEG."""
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = im.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    im = im.crop((left, top, left + side, top + side))
    if side != size:
        im = im.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True, progressive=False)
    return buf.getvalue()


# ------------------------------------------------- hosting JPEG (GitHub Release)
def gh_api(url, data=None, method=None, timeout=60):
    headers = {
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "blog-centralcats-ig",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def ensure_release():
    """Ambil (atau buat) release ber-tag `ig-images` sebagai wadah gambar IG."""
    base = f"https://api.github.com/repos/{GH_REPO}/releases"
    status, rel = gh_api(f"{base}/tags/{RELEASE_TAG}")
    if status == 200:
        return rel
    status, rel = gh_api(base, data={
        "tag_name": RELEASE_TAG,
        "name": "Gambar Instagram",
        "body": ("Wadah gambar JPEG untuk auto-posting Instagram "
                 "(dibuat otomatis oleh scripts/post_instagram.py). "
                 "Jangan dihapus selama fitur auto-post aktif."),
        "draft": False,
        "prerelease": False,
    })
    if status in (200, 201):
        return rel
    warn(f"gagal menyiapkan release '{RELEASE_TAG}' (HTTP {status}): {rel}")
    return None


def upload_asset(release, name, blob, content_type="image/jpeg"):
    """Unggah blob sebagai asset release. Return URL publik atau None.

    `content_type` dibuat parameter (default JPEG, perilaku lama) supaya mode
    pratinjau bisa menitipkan `preview-<slug>.json` di release yang sama.
    """
    # Hapus asset lama bernama sama agar bisa di-upload ulang.
    for a in release.get("assets", []):
        if a.get("name") == name:
            gh_api(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}",
                   method="DELETE")

    url = (f"https://uploads.github.com/repos/{GH_REPO}/releases/"
           f"{release['id']}/assets?name={urllib.parse.quote(name)}")
    req = urllib.request.Request(url, data=blob, method="POST", headers={
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": content_type,
        "User-Agent": "blog-centralcats-ig",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
            return data.get("browser_download_url")
    except urllib.error.HTTPError as e:
        warn(f"gagal unggah asset ke release (HTTP {e.code}): "
             f"{e.read().decode('utf-8', 'replace')[:200]}")
    except Exception as e:
        warn(f"gagal unggah asset ke release: {e}")
    return None


def delete_asset(release, name):
    """Hapus asset release bernama `name` bila ada.

    Dipakai untuk membuang `preview-<slug>.json` setelah artikelnya BENAR-BENAR
    tayang. POS membaca daftar asset `preview-*.json` sebagai antrean "menunggu
    tayang"; tanpa pembersihan ini, antrean itu tak pernah kosong dan artikel
    yang sudah diposting akan terus tampil seolah masih menunggu.
    """
    for a in release.get("assets", []):
        if a.get("name") == name:
            gh_api(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}",
                   method="DELETE")
            print(f"  pratinjau dibersihkan: {name}")
            return True
    return False


def is_public(url):
    """Pastikan URL bisa diambil TANPA autentikasi (Instagram mengunduhnya sendiri)."""
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status == 200 and r.read(512) != b""
    except Exception as e:
        warn(f"URL gambar tidak bisa diakses publik ({url}): {e}. "
             "Pastikan repo ini PUBLIC — Instagram harus bisa mengunduh gambar.")
        return False


# ------------------------------------------------------------------- publish
def wait_container(creation_id):
    """Tunggu container siap (IG mengunduh gambarnya dulu). Biasanya cepat."""
    for _ in range(10):
        s, st = http_json(
            f"{GRAPH}/{creation_id}?fields=status_code,status"
            f"&access_token={urllib.parse.quote(IG_TOKEN)}")
        code = st.get("status_code") if isinstance(st, dict) else None
        if code == "FINISHED":
            return True
        if code == "ERROR":
            warn(f"container ERROR: {st}")
            return False
        time.sleep(3)
    return True  # lanjutkan saja; media_publish akan menolak bila memang belum siap


def publish(image_urls, caption):
    """Content Publishing 2 langkah: buat container -> publish.

    Satu gambar  -> container biasa.
    Banyak gambar -> CAROUSEL: tiap gambar jadi container `is_carousel_item`,
    lalu digabung ke container `media_type=CAROUSEL`. Batas IG 2-10 item, jadi
    daftar dipotong di 10; kalau tersisa 1 gambar, otomatis kembali ke pos biasa.
    """
    if isinstance(image_urls, str):
        image_urls = [image_urls]
    image_urls = [u for u in image_urls if u][:10]
    if not image_urls:
        return None

    if len(image_urls) == 1:
        status, res = http_json(f"{GRAPH}/{IG_USER_ID}/media", data={
            "image_url": image_urls[0],
            "caption": caption,
            "access_token": IG_TOKEN,
        })
        if status >= 300 or not isinstance(res, dict) or "id" not in res:
            warn(f"gagal membuat media container (HTTP {status}): {res}")
            return None
        creation_id = res["id"]
        if not wait_container(creation_id):
            return None
    else:
        children = []
        for u in image_urls:
            status, res = http_json(f"{GRAPH}/{IG_USER_ID}/media", data={
                "image_url": u,
                "is_carousel_item": "true",
                "access_token": IG_TOKEN,
            })
            if status >= 300 or not isinstance(res, dict) or "id" not in res:
                warn(f"gagal membuat item carousel (HTTP {status}): {res}")
                continue
            if wait_container(res["id"]):
                children.append(res["id"])
        # Carousel butuh MINIMAL 2 item. Kalau cuma 1 yang lolos, jangan gagal
        # total — turunkan jadi postingan foto tunggal.
        if len(children) < 2:
            warn(f"hanya {len(children)} item carousel yang siap — "
                 "turun ke postingan foto tunggal.")
            return publish(image_urls[:1], caption)
        status, res = http_json(f"{GRAPH}/{IG_USER_ID}/media", data={
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": IG_TOKEN,
        })
        if status >= 300 or not isinstance(res, dict) or "id" not in res:
            warn(f"gagal membuat container carousel (HTTP {status}): {res}")
            return None
        creation_id = res["id"]
        if not wait_container(creation_id):
            return None

    status, res = http_json(f"{GRAPH}/{IG_USER_ID}/media_publish", data={
        "creation_id": creation_id,
        "access_token": IG_TOKEN,
    })
    if status >= 300 or not isinstance(res, dict) or "id" not in res:
        warn(f"gagal publish (HTTP {status}): {res}")
        return None
    return res["id"]


def page_token():
    """Pages API butuh token HALAMAN, bukan token system user. Tukar dulu."""
    s, res = http_json(f"{GRAPH}/{FB_PAGE_ID}?fields=access_token"
                       f"&access_token={urllib.parse.quote(IG_TOKEN)}")
    if isinstance(res, dict) and res.get("access_token"):
        return res["access_token"]
    warn(f"gagal mengambil token Halaman FB (HTTP {s}): {res}. "
         "Pastikan token punya izin 'pages_manage_posts' & 'pages_show_list'.")
    return None


def post_facebook(image_urls, message, tok):
    """Posting foto + teks ke Halaman FB. Beda dari IG: tautan BISA diklik.

    Satu foto  -> `POST /{page}/photos` langsung terbit (perilaku lama).
    Banyak foto -> tiap foto diunggah dulu dengan `published=false` (jadi TIDAK
    muncul sendiri-sendiri di linimasa), lalu id-nya dirangkai ke satu postingan
    lewat `POST /{page}/feed` + `attached_media`. Ini alur Pages API yang memang
    berbeda dari carousel IG — tidak ada endpoint yang sama untuk keduanya.
    """
    if isinstance(image_urls, str):
        image_urls = [image_urls]
    image_urls = [u for u in image_urls if u]
    if not image_urls:
        return None

    if len(image_urls) == 1:
        status, res = http_json(f"{GRAPH}/{FB_PAGE_ID}/photos", data={
            "url": image_urls[0],
            "caption": message,
            "published": "true",
            "access_token": tok,
        })
        if status >= 300 or not isinstance(res, dict) or not res.get("id"):
            warn(f"gagal posting ke Halaman FB (HTTP {status}): {res}")
            return None
        return res.get("post_id") or res["id"]

    media_ids = []
    for u in image_urls:
        status, res = http_json(f"{GRAPH}/{FB_PAGE_ID}/photos", data={
            "url": u,
            "published": "false",   # jangan terbit sendiri; hanya bahan lampiran
            "access_token": tok,
        })
        if status >= 300 or not isinstance(res, dict) or not res.get("id"):
            warn(f"gagal mengunggah foto FB (HTTP {status}): {res}")
            continue
        media_ids.append(res["id"])

    if not media_ids:
        return None

    data = {"message": message, "access_token": tok}
    for i, mid in enumerate(media_ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": mid})
    status, res = http_json(f"{GRAPH}/{FB_PAGE_ID}/feed", data=data)
    if status >= 300 or not isinstance(res, dict) or not res.get("id"):
        warn(f"gagal posting multi-foto ke Halaman FB (HTTP {status}): {res}")
        return None
    return res.get("post_id") or res["id"]


# ---------------------------------------------------------------------- main
def extra_photos(fm, animals, want):
    """Cari `want` foto TAMBAHAN untuk carousel, di luar gambar unggulan artikel.

    Relevansi dijaga dua lapis:
    1. Kata kunci — memakai `image_query` / `image_query_fallback` yang DISIMPAN
       generate_drafts.py di front matter (spesifik ke isi artikel, mis.
       "cat ear close up"), bukan menebak ulang dari judul. Artikel lama yang
       belum punya field itu jatuh ke nama hewan saja.
    2. Gemini vision — tiap kandidat dicek `verify_photo()`; yang subjeknya tak
       terlihat dibuang. Fail-closed: ragu = tolak.

    Lapis 1 menjaga foto nyambung ke TOPIK, lapis 2 menjamin HEWANNYA benar.
    Kalau hasilnya kurang dari yang diminta, itu disengaja — lebih baik carousel
    pendek daripada diisi foto yang tidak berkaitan.
    """
    if want <= 0:
        return []
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import generate_drafts as g
    except SystemExit as e:   # generate_drafts sys.exit bila GEMINI_API_KEY kosong
        notice(f"carousel dilewati — {e}")
        return []
    except Exception as e:
        notice(f"carousel dilewati — tidak bisa memuat generate_drafts: {e}")
        return []

    animal_en = g.ANIMAL_EN.get(animals[0], animals[0])
    queries = [q for q in (field("image_query", fm),
                           field("image_query_fallback", fm),
                           animal_en) if q]
    # Subjek verifikasi: pakai `image_subject` (artikel ras) bila ada, selain itu
    # nama hewannya. Ini menjamin HEWAN yang benar terlihat di foto; kaitan ke
    # topik artikel datang dari kata kunci di atas.
    subject = field("image_subject", fm) or animals[0]
    print(f"  carousel: cari {want} foto tambahan, query={queries}, "
          f"verifikasi subjek \"{subject}\"")
    try:
        return g.fetch_photos_bytes(queries, subject=subject, count=want)
    except Exception as e:
        warn(f"gagal mengambil foto carousel: {e}")
        return []


def write_preview(release, slug, payload):
    """Titipkan pratinjau sebagai `preview-<slug>.json` di release `ig-images`.

    Repo ini PUBLIC, jadi POS cukup mengambilnya lewat URL tanpa autentikasi —
    pola yang sama dengan gambar JPEG (dan tetap tidak menambah biner ke histori
    git, lihat CLAUDE.md Bagian 8a).
    """
    blob = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    url = upload_asset(release, f"preview-{slug}.json", blob, "application/json")
    if url:
        print(f"[PRATINJAU] {slug} -> {url}")
    return url


def main():
    # Pratinjau tidak menyentuh Graph API, jadi token IG tak wajib ada.
    if not DRY_RUN and (not IG_USER_ID or not IG_TOKEN):
        notice("IG_USER_ID / IG_ACCESS_TOKEN belum diset — auto-post dilewati.")
        return
    if not FILES:
        notice("tidak ada artikel baru — tidak ada yang diposting.")
        return
    if not HAS_PIL:
        warn("Pillow tidak terpasang — tidak bisa konversi gambar ke JPEG. Dilewati.")
        return
    if not GH_REPO or not GH_TOKEN:
        warn("GITHUB_REPOSITORY / GITHUB_TOKEN kosong — tidak bisa menghosting JPEG. Dilewati.")
        return

    release = ensure_release()
    if not release:
        return

    # Token Halaman diambil sekali di depan; bila gagal, IG tetap jalan.
    fb_token = None
    if FB_PAGE_ID and not DRY_RUN:
        fb_token = page_token()
        if not fb_token:
            notice("posting Halaman Facebook dilewati — Instagram tetap diproses.")

    posted = posted_fb = previewed = 0
    ringkasan = []  # pratinjau yang terbentuk -> dipakai notify_social_email.py
    for f in FILES:
        parts = pathlib.PurePosixPath(f.replace("\\", "/")).parts
        if (len(parts) < 3 or parts[0] != "content"
                or not f.endswith(".md") or parts[-1] == "_index.md"):
            print(f"  lewati (bukan artikel ber-section): {f}")
            continue
        p = pathlib.Path(f)
        if not p.exists():
            print(f"  lewati (file tak ada di checkout): {f}")
            continue

        fm, body = split_doc(p.read_text(encoding="utf-8"))
        if re.search(r'(?m)^\s*draft\s*=\s*true', fm):
            print(f"  lewati (draft=true): {f}")
            continue

        title = field("title", fm) or "Artikel baru"

        # Medsos hanya memuat hewan tertentu (kucing & anjing) — kriteria ini
        # SENGAJA beda dari blog, yang memuat semua hewan (CLAUDE.md Bagian 8 & 13).
        # `hewan` kosong dianggap kucing (default blog, lihat Bagian 3).
        animals = [a.lower() for a in list_field("hewan", fm)] or ["kucing"]
        if SOCIAL_ANIMALS and not any(a in SOCIAL_ANIMALS for a in animals):
            notice(f"'{title}' di luar cakupan medsos (hewan: {', '.join(animals)}; "
                   f"yang diposting: {', '.join(SOCIAL_ANIMALS)}) — dilewati.")
            continue

        img_path = first_image(fm)
        if not img_path:
            notice(f"'{title}' tidak punya gambar unggulan — dilewati "
                   "(Instagram & Facebook wajib pakai gambar).")
            continue

        raw = load_image_bytes(img_path)
        if not raw:
            continue
        try:
            jpeg = to_square_jpeg(raw)
        except Exception as e:
            warn(f"gagal konversi gambar '{img_path}' ke JPEG: {e}")
            continue

        stem = pathlib.PurePosixPath(img_path).stem
        image_url = upload_asset(release, stem + ".jpg", jpeg)
        if not image_url or not is_public(image_url):
            continue

        # Carousel: gambar unggulan jadi slide pertama, sisanya foto tambahan
        # yang relevan. Kredit fotografer dikumpulkan untuk ditulis di caption.
        image_urls = [image_url]
        credits = []
        for i, ph in enumerate(extra_photos(fm, animals, CAROUSEL_MAX - 1), start=2):
            try:
                j = to_square_jpeg(ph["bytes"])
            except Exception as e:
                warn(f"gagal konversi foto carousel #{i}: {e}")
                continue
            u = upload_asset(release, f"{stem}-{i}.jpg", j)
            if u and is_public(u):
                image_urls.append(u)
                if ph.get("credit"):
                    credits.append(ph["credit"])
        if len(image_urls) > 1:
            print(f"  carousel siap: {len(image_urls)} gambar")

        url = article_url(f)

        slug = p.stem
        # Caption dibangun sekali di sini supaya yang DITINJAU di POS benar-benar
        # sama dengan yang nanti diposting (seed = slug, jadi deterministik).
        caption_ig = build_caption(title, fm, body, seed=slug)
        caption_fb = build_caption(title, fm, body, url, seed=slug)

        if DRY_RUN:
            entri = {
                "slug": slug,
                "path": f,
                "title": title,
                "article_url": url,
                # JPEG 1080x1080 hasil crop, persis yang akan tayang. `image_url`
                # dipertahankan (= slide pertama) supaya konsumen lama tak pecah.
                "image_url": image_url,
                "image_urls": image_urls,
                "carousel": len(image_urls) > 1,
                "photo_credits": credits,
                "hewan": animals,
                "caption_instagram": caption_ig,
                "caption_facebook": caption_fb,
            }
            if write_preview(release, slug, entri):
                previewed += 1
                ringkasan.append(entri)
            continue

        media_id = publish(image_urls, caption_ig)
        if media_id:
            posted += 1
            print(f"[IG] {title} -> media id {media_id} "
                  f"({len(image_urls)} gambar) ({url})")

        # Halaman FB: tautan BISA diklik di sini, jadi permalink ikut dimuat.
        # Catatan: setelan crosspost IG->FB TIDAK berlaku untuk postingan yang
        # diterbitkan lewat Graph API, jadi Halaman harus diposting terpisah.
        if FB_PAGE_ID and fb_token:
            post_id = post_facebook(image_urls, caption_fb, fb_token)
            if post_id:
                posted_fb += 1
                print(f"[FB] {title} -> post id {post_id} ({url})")

        # Sudah tayang -> keluarkan dari antrean POS. Hanya kalau IG berhasil:
        # kalau gagal, pratinjaunya harus tetap ada supaya bisa dicoba lagi.
        if media_id:
            delete_asset(release, f"preview-{slug}.json")

    if DRY_RUN:
        # Ditulis ke file supaya langkah email di workflow tahu apa yang harus
        # diberitahukan. Tanpa ini pratinjau terbentuk diam-diam: panel Media
        # Sosial di POS belum ada, jadi email adalah satu-satunya saluran yang
        # benar-benar sampai ke admin.
        if ringkasan:
            pathlib.Path(SUMMARY_FILE).write_text(
                json.dumps(ringkasan, ensure_ascii=False), encoding="utf-8")
        notice(f"pratinjau selesai. {previewed} artikel siap ditinjau di POS. "
               "Belum ada yang diposting.")
    else:
        notice(f"selesai. {posted} postingan Instagram, "
               f"{posted_fb} postingan Halaman Facebook.")


if __name__ == "__main__":
    main()
