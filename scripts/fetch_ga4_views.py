#!/usr/bin/env python3
"""Tarik jumlah pageview per artikel dari GA4, simpan ke data/views.json.

Dipakai workflow .github/workflows/ga4-views.yml (harian). Hugo membaca berkas
itu lewat site.Data.views di layouts/_default/single.html, jadi angkanya ditanam
ke HTML saat build -- NOL request tambahan untuk pengunjung. Sengaja dipilih
daripada penghitung real-time supaya Aturan Performa (CLAUDE.md Bagian 4) tidak
dilanggar.

Butuh dua env:
  GA4_PROPERTY_ID  -> ID properti GA4 (ANGKA, mis. 412345678). BUKAN G-SGYPJC015Y.
  GOOGLE_APPLICATION_CREDENTIALS -> path JSON service account yang sudah diberi
                                    peran Viewer di properti GA4 tersebut.

Gagal = keluar kode 1 TANPA menulis berkas, supaya data lama tetap dipakai dan
halaman tidak mendadak kehilangan angkanya.
"""
import json
import os
import sys
from datetime import date

MULAI = "2020-01-01"          # jauh ke belakang = akumulasi sejak awal properti
BATAS_BARIS = 100000
NL = chr(10)                  # sengaja chr(10), bukan escape: berkas ini pernah
                              # ditulis lewat shell yang memakan backslash

def bersihkan(path):
    """Normalkan pagePath GA4 supaya cocok dengan RelPermalink Hugo."""
    for pemisah in ("?", "#"):
        if pemisah in path:
            path = path.split(pemisah, 1)[0]
    if not path.startswith("/"):
        return None
    if not path.endswith("/"):
        path = path + "/"
    return path

def utama():
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop:
        print("GA4_PROPERTY_ID kosong", file=sys.stderr)
        return 1
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("GOOGLE_APPLICATION_CREDENTIALS kosong", file=sys.stderr)
        return 1

    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest,
    )

    klien = BetaAnalyticsDataClient()
    laporan = klien.run_report(RunReportRequest(
        property="properties/" + prop,
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date=MULAI, end_date="today")],
        limit=BATAS_BARIS,
    ))

    views = {}
    for baris in laporan.rows:
        path = bersihkan(baris.dimension_values[0].value or "")
        if not path:
            continue
        try:
            jumlah = int(baris.metric_values[0].value)
        except (TypeError, ValueError):
            continue
        # Dijumlahkan: beberapa varian path menyatu setelah dinormalkan.
        views[path] = views.get(path, 0) + jumlah

    if not views:
        print("GA4 tidak mengembalikan baris -- berkas TIDAK ditimpa", file=sys.stderr)
        return 1

    os.makedirs("data", exist_ok=True)
    tujuan = os.path.join("data", "views.json")
    with open(tujuan, "w", encoding="utf-8", newline=NL) as f:
        json.dump(dict(sorted(views.items())), f, ensure_ascii=False, indent=1)
        f.write(NL)
    print("Ditulis " + tujuan + ": " + str(len(views)) + " path, per " + str(date.today()))
    return 0

if __name__ == "__main__":
    sys.exit(utama())
