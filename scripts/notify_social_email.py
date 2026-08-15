#!/usr/bin/env python3
"""Kirim email ke admin saat PRATINJAU MEDSOS siap ditinjau.

Kenapa ada: sejak medsos diberi gerbang tinjau, artikel baru TIDAK lagi otomatis
tayang ke Instagram/Facebook — ia hanya menghasilkan `preview-<slug>.json`. Padahal
panel Media Sosial di POS belum dibangun, dan `post-instagram.yml` tidak pernah
mengirim email. Akibatnya pratinjau bisa mengendap tanpa ada yang tahu, dan medsos
diam-diam berhenti terisi. Email ini menutup lubang itu.

Dipanggil `.github/workflows/post-instagram.yml` setelah langkah pratinjau, membaca
ringkasan yang ditulis `post_instagram.py`. Hanya pustaka standar (tanpa pip).

Env:
- RESEND_API_KEY  (wajib; kalau kosong -> dilewati, tidak menggagalkan job)
- PREVIEW_SUMMARY (path file ringkasan; default preview-summary.json)
- RUN_URL         (opsional; tautan run Actions yang menghasilkan pratinjau)
- REPO            (opsional; "owner/repo" untuk merakit tautan "Tayangkan")
"""
import os
import sys
import json
import html
import pathlib
import urllib.request
import urllib.error

API_KEY = (os.environ.get("RESEND_API_KEY") or "").strip()
SUMMARY = (os.environ.get("PREVIEW_SUMMARY") or "preview-summary.json").strip()
RUN_URL = (os.environ.get("RUN_URL") or "").strip()
REPO = (os.environ.get("REPO") or "").strip()
TO = "centralcatgrooming@gmail.com"
FROM = "Central Cat's <noreply@centralcats.id>"

if not API_KEY:
    print("RESEND_API_KEY belum diset — email pratinjau medsos dilewati.")
    sys.exit(0)

p = pathlib.Path(SUMMARY)
if not p.exists():
    print("Tidak ada pratinjau baru — email dilewati.")
    sys.exit(0)
try:
    items = json.loads(p.read_text(encoding="utf-8"))
except Exception as e:
    print(f"Ringkasan pratinjau tak terbaca ({e}) — email dilewati.")
    sys.exit(0)
if not items:
    print("Ringkasan pratinjau kosong — email dilewati.")
    sys.exit(0)

# Tombol mengarah ke halaman workflow, tempat "Run workflow" dengan posting: true.
# Saat panel Media Sosial di POS jadi, ganti tautan ini ke POS.
aksi = (f"https://github.com/{REPO}/actions/workflows/post-instagram.yml"
        if REPO else RUN_URL)


def potong(s, n=180):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n].rstrip() + "…"


kartu = ""
for it in items:
    judul = html.escape(it.get("title") or it.get("slug") or "Artikel")
    gambar = it.get("image_urls") or ([it["image_url"]] if it.get("image_url") else [])
    n = len(gambar)
    label = f"Carousel {n} gambar" if n > 1 else "1 gambar"
    cap = html.escape(potong(it.get("caption_instagram")))
    thumb = html.escape(gambar[0]) if gambar else ""
    kartu += f"""
      <div style="border:1px solid #eee;border-radius:12px;overflow:hidden;margin:0 0 14px">
        {'<img src="' + thumb + '" width="480" style="display:block;width:100%;max-width:480px;height:auto" alt="">' if thumb else ''}
        <div style="padding:14px 16px">
          <p style="margin:0 0 4px;font-size:14px;font-weight:700;color:#3D2010">{judul}</p>
          <p style="margin:0 0 8px;font-size:11px;color:#E8793A;font-weight:700">{label}</p>
          <p style="margin:0;font-size:12px;color:#666;line-height:1.6">{cap}</p>
        </div>
      </div>"""

jml = len(items)
judul_email = (f"📸 {jml} pratinjau medsos siap ditinjau"
               if jml > 1 else "📸 Pratinjau medsos siap ditinjau")

html_body = f"""<div style="font-family:Segoe UI,Arial,sans-serif;background:#f5f0eb;padding:24px">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden">
    <div style="background:#3D2010;padding:20px 24px;text-align:center">
      <p style="margin:0;color:#ffffff;font-size:16px;font-weight:800">Central Cat's — Media Sosial</p>
    </div>
    <div style="padding:24px">
      <p style="margin:0 0 8px;font-size:15px;color:#3D2010;font-weight:700">{html.escape(judul_email)}</p>
      <p style="margin:0 0 18px;font-size:13px;color:#666;line-height:1.6">
        Artikel baru sudah terbit di blog. Foto &amp; caption untuk Instagram dan Halaman
        Facebook sudah disiapkan, tapi <b>belum tayang</b> — menunggu persetujuan Anda.
      </p>
      {kartu}
      <div style="text-align:center;margin-top:18px">
        <a href="{html.escape(aksi)}" style="display:inline-block;background:#E8793A;color:#ffffff;font-size:14px;font-weight:700;padding:13px 30px;border-radius:50px;text-decoration:none">Tinjau &amp; tayangkan &rarr;</a>
      </div>
      <p style="margin:16px 0 0;font-size:11px;color:#999;line-height:1.6">
        Jalankan workflow dengan <b>posting: true</b> untuk menayangkan.
        Caption Instagram <b>tidak bisa diedit setelah tayang</b> — periksa dulu.
      </p>
    </div>
    <div style="background:#faf6f1;padding:14px 24px;text-align:center">
      <p style="margin:0;color:#aaa;font-size:11px">Email otomatis — tidak ada yang tayang tanpa persetujuan.</p>
    </div>
  </div>
</div>"""

payload = {"from": FROM, "to": [TO], "subject": judul_email + " — Central Cat's",
           "html": html_body}

req = urllib.request.Request(
    "https://api.resend.com/emails",
    data=json.dumps(payload).encode("utf-8"),
    method="POST",
)
req.add_header("Authorization", "Bearer " + API_KEY)
req.add_header("Content-Type", "application/json")
# WAJIB. Tanpa User-Agent kustom, urllib mengirim "Python-urllib/3.x" dan
# Cloudflare di depan Resend menolaknya dengan HTTP 403 "error code: 1010"
# (blokir berdasarkan signature klien). Sama persis dengan notify_draft_email.py.
req.add_header("User-Agent", "central-cats-blog-automation/1.0")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Email pratinjau medsos terkirim ({jml} artikel), HTTP {r.status}")
except urllib.error.HTTPError as e:
    print(f"::warning::gagal kirim email pratinjau medsos (HTTP {e.code}): "
          f"{e.read().decode('utf-8', 'replace')[:200]}")
except Exception as e:
    print(f"::warning::gagal kirim email pratinjau medsos: {e}")
