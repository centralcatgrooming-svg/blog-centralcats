#!/usr/bin/env python3
"""Ping IndexNow untuk artikel BARU agar cepat ditemukan mesin pencari yang
mendukung protokol IndexNow (mis. Bing, Yandex). CATATAN: Google TIDAK
mendukung IndexNow — untuk Google andalkan sitemap + internal link + (bila
perlu) "Request Indexing" manual di Search Console.

Non-blocking: skrip ini TIDAK boleh menggagalkan job apa pun. Semua error
ditangkap dan hanya dicetak sebagai ::warning::.

Env:
  NEW_FILES  daftar path artikel baru (dipisah baris/koma), mis:
             content/panduan-tips/grooming-kucing-pasar-kemis.md
"""
import os
import json
import urllib.request
import urllib.error

# Kunci IndexNow (PUBLIK by design — disajikan di https://<host>/<KEY>.txt).
KEY = "f4efa60d1fc581fb45be07ed3edb7d94"
HOST = "blog.centralcats.id"
BASE = f"https://{HOST}/"
KEY_LOCATION = f"{BASE}{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def file_to_url(path):
    """content/<section>/<slug>.md -> https://<host>/<section>/<slug>/"""
    path = path.strip().strip('"').strip()
    if not path.endswith(".md"):
        return None
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if not parts or parts[-1] == "_index.md":
        return None
    if "content" not in parts:
        return None
    rel = parts[parts.index("content") + 1:]
    if len(rel) < 2:  # butuh <section>/<slug>.md
        return None
    section = rel[0]
    slug = rel[-1][:-3]  # buang ".md"
    return f"{BASE}{section}/{slug}/"


def main():
    raw = os.environ.get("NEW_FILES", "")
    urls = []
    for line in raw.replace(",", "\n").splitlines():
        u = file_to_url(line)
        if u and u not in urls:
            urls.append(u)

    if not urls:
        print("::notice::IndexNow: tidak ada URL artikel baru untuk dikirim.")
        return

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"::notice::IndexNow OK ({resp.status}) untuk {len(urls)} URL: "
                  + ", ".join(urls))
    except urllib.error.HTTPError as e:
        # 200/202 = sukses. 4xx = masalah kunci/format. Jangan gagalkan job.
        body = e.read().decode("utf-8", "ignore")[:200]
        print(f"::warning::IndexNow HTTP {e.code} (dilewati): {body}")
    except Exception as e:
        print(f"::warning::IndexNow gagal (dilewati): {e}")


if __name__ == "__main__":
    main()
