#!/usr/bin/env python3
"""Kirim notifikasi push OneSignal untuk ARTIKEL BARU.

Dipanggil oleh .github/workflows/notify-new-post.yml saat ada file artikel baru
(ditambahkan) di push ke main. Hanya memakai pustaka standar (tanpa pip install).

Env:
- ONESIGNAL_APP_ID         App ID (publik).
- ONESIGNAL_REST_API_KEY   API/REST key (RAHASIA, dari GitHub Secret).
- BASE_URL                 mis. "https://blog.centralcats.id/".
- NEW_FILES                daftar path artikel baru (1 per baris), dari git diff.

Aman bila belum ada subscriber: error "no recipients" dari OneSignal hanya dicatat,
tidak menggagalkan job.
"""
import os
import re
import sys
import json
import pathlib
import urllib.request
import urllib.error

APP_ID = (os.environ.get("ONESIGNAL_APP_ID") or "").strip()
API_KEY = (os.environ.get("ONESIGNAL_REST_API_KEY") or "").strip()
BASE_URL = ((os.environ.get("BASE_URL") or "https://blog.centralcats.id/").strip().rstrip("/")) + "/"
FILES = [f.strip() for f in (os.environ.get("NEW_FILES") or "").splitlines() if f.strip()]

ENDPOINT = "https://api.onesignal.com/notifications"
FM_RE = re.compile(r'^\+\+\+\s*\n(.*?)\n\+\+\+\s*$', re.S | re.M)


def front_matter(text):
    m = FM_RE.search(text)
    return m.group(1) if m else ""


def field(name, fm):
    m = re.search(r'(?m)^\s*%s\s*=\s*"(.*?)"' % re.escape(name), fm)
    return m.group(1) if m else ""


def first_image(fm):
    m = re.search(r'(?m)^\s*images\s*=\s*\[\s*"([^"]+)"', fm)
    return m.group(1) if m else ""


def article_url(path):
    """content/<section>/<slug>.md -> BASE/<section>/<slug>/"""
    p = pathlib.PurePosixPath(path)
    return BASE_URL + p.parts[-2] + "/" + p.stem + "/"


def send(title, url, image):
    payload = {
        "app_id": APP_ID,
        "target_channel": "push",
        "included_segments": ["Subscribed Users"],
        "headings": {"en": "Artikel baru — Central Cat's News"},
        "contents": {"en": title},
        "url": url,
    }
    if image:
        payload["chrome_web_image"] = image if image.startswith("http") else BASE_URL.rstrip("/") + image
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Key " + API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    if not APP_ID or not API_KEY:
        sys.exit("ONESIGNAL_APP_ID / ONESIGNAL_REST_API_KEY belum diset (cek Secrets).")
    if not FILES:
        print("Tidak ada artikel baru. Tidak ada notifikasi dikirim.")
        return

    sent = 0
    for f in FILES:
        parts = pathlib.PurePosixPath(f).parts
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
        url = article_url(f)
        status, body = send(title, url, first_image(fm))
        ok = 200 <= status < 300
        tag = "[KIRIM]" if ok else "[INFO]"
        print(f"{tag} ({status}) {title} -> {url}")
        print(f"        resp: {body}")
        if ok:
            sent += 1

    print(f"\nSelesai. {sent} notifikasi terkirim.")


if __name__ == "__main__":
    main()
