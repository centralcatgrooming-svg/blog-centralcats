#!/usr/bin/env python3
"""Kirim email PENGINGAT ke admin saat draf artikel baru dibuat.

Dipanggil oleh .github/workflows/auto-draft.yml setelah PR draf dibuat.
Email = pengingat ringkas + tombol "Tinjau di Pusat Konten" (POS). Isi artikel
DIBACA & DISETUJUI di POS, bukan di email. Hanya pustaka standar (tanpa pip).

Env:
- RESEND_API_KEY  (wajib; kalau kosong → dilewati, tidak menggagalkan job)
- PR_NUMBER       (opsional; nomor PR untuk referensi di teks)
"""
import os
import sys
import json
import urllib.request
import urllib.error

API_KEY = (os.environ.get("RESEND_API_KEY") or "").strip()
PR_NUMBER = (os.environ.get("PR_NUMBER") or "").strip()

POS_URL = "https://app.centralcats.id/technology-system"
TO = "centralcatgrooming@gmail.com"
FROM = "Central Cat's <noreply@centralcats.id>"

if not API_KEY:
    print("RESEND_API_KEY belum diset — email pengingat dilewati.")
    sys.exit(0)

ref = f" (#{PR_NUMBER})" if PR_NUMBER else ""
html = f"""<div style="font-family:Segoe UI,Arial,sans-serif;background:#f5f0eb;padding:24px">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden">
    <div style="background:#3D2010;padding:20px 24px;text-align:center">
      <p style="margin:0;color:#ffffff;font-size:16px;font-weight:800">Central Cat's — Pusat Konten</p>
    </div>
    <div style="padding:24px">
      <p style="margin:0 0 8px;font-size:15px;color:#3D2010;font-weight:700">📝 Draf artikel baru siap ditinjau</p>
      <p style="margin:0 0 20px;font-size:13px;color:#666;line-height:1.6">AI sudah membuat draf artikel baru{ref}. Tinjau isinya lalu setujui untuk terbit — langsung dari POS.</p>
      <div style="text-align:center">
        <a href="{POS_URL}" style="display:inline-block;background:#E8793A;color:#ffffff;font-size:14px;font-weight:700;padding:13px 30px;border-radius:50px;text-decoration:none">Tinjau di Pusat Konten &rarr;</a>
      </div>
    </div>
    <div style="background:#faf6f1;padding:14px 24px;text-align:center">
      <p style="margin:0;color:#aaa;font-size:11px">Email otomatis — buka POS untuk menyetujui / menolak.</p>
    </div>
  </div>
</div>"""

payload = {
    "from": FROM,
    "to": [TO],
    "subject": "📝 Draf artikel baru siap ditinjau — Pusat Konten",
    "html": html,
}

req = urllib.request.Request(
    "https://api.resend.com/emails",
    data=json.dumps(payload).encode("utf-8"),
    method="POST",
)
req.add_header("Authorization", "Bearer " + API_KEY)
req.add_header("Content-Type", "application/json")
req.add_header("User-Agent", "central-cats-blog-automation/1.0")

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"[KIRIM] ({r.status}) email pengingat -> {TO}")
        print(r.read().decode("utf-8", "replace"))
except urllib.error.HTTPError as e:
    print(f"[INFO] ({e.code}) gagal kirim email: {e.read().decode('utf-8', 'replace')}")
except Exception as e:
    print(f"[INFO] gagal kirim email: {e}")
