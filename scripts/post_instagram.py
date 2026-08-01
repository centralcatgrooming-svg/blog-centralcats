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
GRAPH_VERSION = (os.environ.get("IG_GRAPH_VERSION") or "v21.0").strip()
BASE_URL = ((os.environ.get("BASE_URL") or "https://blog.centralcats.id/").strip().rstrip("/")) + "/"
FILES = [f.strip() for f in (os.environ.get("NEW_FILES") or "").splitlines() if f.strip()]

GH_REPO = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
GH_TOKEN = (os.environ.get("GITHUB_TOKEN") or "").strip()
RELEASE_TAG = "ig-images"

GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
FM_RE = re.compile(r'^\+\+\+\s*\n(.*?)\n\+\+\+\s*$', re.S | re.M)

# Hashtag tetap milik brand. Sisanya diturunkan dari `tags`/`hewan` artikel.
BRAND_TAGS = ["centralcats", "groomingkucing", "petshoptangerang", "pasarkemis", "rajeg"]
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
def front_matter(text):
    m = FM_RE.search(text)
    return m.group(1) if m else ""


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


def build_caption(title, summary, fm):
    """Caption IG. Ingat: link di caption TIDAK bisa diklik -> arahkan ke bio."""
    parts = [title]
    if summary:
        parts.append(summary)
    parts.append(
        "Baca artikel lengkapnya di blog kami — tautan ada di bio \U0001f517\n"
        "Central Cat's — grooming, petshop & cat hotel di Pasar Kemis & Rajeg."
    )
    tags = hashtags(fm)
    if tags:
        parts.append(tags)
    caption = "\n\n".join(parts)
    if len(caption) > MAX_CAPTION:
        caption = caption[:MAX_CAPTION - 1].rstrip() + "…"
    return caption


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


def upload_asset(release, name, jpeg):
    """Unggah JPEG sebagai asset release. Return URL publik atau None."""
    # Hapus asset lama bernama sama agar bisa di-upload ulang.
    for a in release.get("assets", []):
        if a.get("name") == name:
            gh_api(f"https://api.github.com/repos/{GH_REPO}/releases/assets/{a['id']}",
                   method="DELETE")

    url = (f"https://uploads.github.com/repos/{GH_REPO}/releases/"
           f"{release['id']}/assets?name={urllib.parse.quote(name)}")
    req = urllib.request.Request(url, data=jpeg, method="POST", headers={
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": "image/jpeg",
        "User-Agent": "blog-centralcats-ig",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
            return data.get("browser_download_url")
    except urllib.error.HTTPError as e:
        warn(f"gagal unggah gambar ke release (HTTP {e.code}): "
             f"{e.read().decode('utf-8', 'replace')[:200]}")
    except Exception as e:
        warn(f"gagal unggah gambar ke release: {e}")
    return None


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
def publish(image_url, caption):
    """2 langkah Content Publishing: buat container -> publish."""
    status, res = http_json(f"{GRAPH}/{IG_USER_ID}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": IG_TOKEN,
    })
    if status >= 300 or not isinstance(res, dict) or "id" not in res:
        warn(f"gagal membuat media container (HTTP {status}): {res}")
        return None
    creation_id = res["id"]

    # Tunggu container siap (IG mengunduh gambar dulu). Biasanya cepat.
    for _ in range(10):
        s, st = http_json(
            f"{GRAPH}/{creation_id}?fields=status_code,status"
            f"&access_token={urllib.parse.quote(IG_TOKEN)}")
        code = st.get("status_code") if isinstance(st, dict) else None
        if code == "FINISHED":
            break
        if code == "ERROR":
            warn(f"container ERROR: {st}")
            return None
        time.sleep(3)

    status, res = http_json(f"{GRAPH}/{IG_USER_ID}/media_publish", data={
        "creation_id": creation_id,
        "access_token": IG_TOKEN,
    })
    if status >= 300 or not isinstance(res, dict) or "id" not in res:
        warn(f"gagal publish (HTTP {status}): {res}")
        return None
    return res["id"]


# ---------------------------------------------------------------------- main
def main():
    if not IG_USER_ID or not IG_TOKEN:
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

    posted = 0
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

        fm = front_matter(p.read_text(encoding="utf-8"))
        if re.search(r'(?m)^\s*draft\s*=\s*true', fm):
            print(f"  lewati (draft=true): {f}")
            continue

        title = field("title", fm) or "Artikel baru"
        img_path = first_image(fm)
        if not img_path:
            notice(f"'{title}' tidak punya gambar unggulan — dilewati "
                   "(Instagram wajib pakai gambar).")
            continue

        raw = load_image_bytes(img_path)
        if not raw:
            continue
        try:
            jpeg = to_square_jpeg(raw)
        except Exception as e:
            warn(f"gagal konversi gambar '{img_path}' ke JPEG: {e}")
            continue

        asset_name = pathlib.PurePosixPath(img_path).stem + ".jpg"
        image_url = upload_asset(release, asset_name, jpeg)
        if not image_url or not is_public(image_url):
            continue

        media_id = publish(image_url, build_caption(title, field("summary", fm), fm))
        if media_id:
            posted += 1
            print(f"[POSTING] {title} -> media id {media_id} ({article_url(f)})")

    notice(f"selesai. {posted} postingan Instagram terkirim.")


if __name__ == "__main__":
    main()
