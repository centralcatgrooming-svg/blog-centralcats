#!/usr/bin/env python3
"""Ubah hasil ekspor Shopee Seller Centre menjadi FEED KATALOG META (CSV).

Feed ini dipakai Instagram Shop / Facebook sebagai **etalase**: pembeli menekan
produk lalu diarahkan ke halaman Shopee untuk bertransaksi. Desain "katalog +
tautan keluar" ini WAJIB, karena Permendag 19/2026 melarang social commerce
memfasilitasi pembayaran langsung di dalam aplikasi (lihat CLAUDE.md Bagian 14).

Butuh 3 file ekspor dari menu **Mass Update** di Shopee Seller Centre:
  1. mass_update_basic_info_<shopid>_<ts>.xlsx  -> nama & deskripsi produk
  2. mass_update_media_info_<shopid>_<ts>.xlsx  -> foto sampul, foto tambahan, kategori
  3. mass_update_sales_info_<shopid>_<ts>.xlsx  -> harga & stok (PER VARIASI)
Ketiganya digabung berdasarkan kolom "Kode Produk".

Pakai:
  python scripts/shopee_to_catalog.py [DIR_EKSPOR] [-o FILE_KELUARAN]
  # DIR_EKSPOR default: folder Downloads. File terbaru per jenis dipilih otomatis.

Tanpa dependensi luar (stdlib saja) — file .xlsx dibaca langsung sebagai zip+XML,
sama seperti skrip lain di repo ini yang sengaja bebas pip install.
"""
import csv
import os
import re
import sys
import glob
import zipfile
import argparse
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

SHOP_ID = "262714770"                      # Central Cat's — ada di nama file ekspor
LINK_TMPL = "https://shopee.co.id/product/{shop}/{item}"
CURRENCY = "IDR"
BRAND_DEFAULT = "Central Cat's"
MAX_TITLE = 200                            # batas judul katalog Meta
MAX_DESC = 9999                            # batas deskripsi katalog Meta
MAX_EXTRA_IMG = 20                         # batas additional_image_link Meta

# Keputusan user (1 Agu 2026): SEMUA produk dimasukkan & ditandai "in stock",
# termasuk yang stoknya 0 di Shopee (~50% katalog). Konsekuensinya sudah
# disampaikan: sebagian pengunjung akan mendarat di produk yang habis.
# Ganti ke False bila nanti ingin availability mengikuti stok sungguhan.
ANGGAP_SELALU_TERSEDIA = True

# Merek yang ada di toko. Dicocokkan di mana saja dalam judul, DIURUTKAN dari
# yang terpanjang supaya "Pro Plan" tidak keburu tertangkap potongan lain.
# Tambahkan di sini bila ada merek baru — ini satu-satunya tempat yang perlu diubah.
MEREK_DIKENAL = sorted([
    # "Royal Care" (obat) adalah merek TERPISAH dari "Royal Canin" (makanan) —
    # keduanya harus terdaftar, jangan disamakan hanya karena diawali "Royal".
    "Body & Tail", "Royal Canin", "Royal Care", "Happy Cat", "Central Cat's", "Sol Latanza",
    "Vets Formula", "Giant Feed", "Koko Pets", "Pokoko Pet", "Life Cat",
    "Genius Spray", "Derma Spray", "Oxy Otic", "ProPlan", "Proplan",
    "Kaniva", "Biolite", "Vitalysine", "Catsrang", "Micromax", "Markotops",
    "Vitasong", "Therafeed", "Vitagold", "Arthacat", "Phoenix", "Luve",
    "Profender", "Haipet", "Purrsona", "Taisho", "Onemed", "Hexamilk",
    "Growssy", "Drontal", "Ilium", "Freshotic", "Catnivore",
], key=len, reverse=True)

# Penyeragaman penulisan merek yang tidak konsisten di judul Shopee.
NORMALISASI_MEREK = {"ProPlan": "Pro Plan", "Proplan": "Pro Plan"}

# Judul yang diawali kata-kata ini = barang generik tanpa merek -> pakai nama toko.
KATA_UMUM = {
    "bowl", "sisir", "kalung", "baju", "collar", "botol", "teaser", "tisu",
    "paket", "galon/dispenser", "pet", "sleeping", "packing", "lint", "sticky",
    "litter", "scoop", "serokan", "selimut", "wood", "underpad", "fungi",
    "miracle", "mandiin", "deep",
}


# ------------------------------------------------------------------ baca xlsx
def _cell_text(c, shared):
    if c.get("t") == "inlineStr":
        return "".join(t.text or "" for t in c.iter(NS + "t"))
    v = c.find(NS + "v")
    if v is None:
        return ""
    if c.get("t") == "s":
        try:
            return shared[int(v.text)]
        except (ValueError, IndexError):
            return ""
    return v.text or ""


def read_sheet(path):
    """Baca .xlsx ekspor Shopee -> list of dict berkunci NAMA KOLOM (bhs Indonesia).

    Format ekspor Shopee tidak biasa: baris 1 = kunci internal (`et_title_*`),
    baris 2 = metadata, **baris 3 = header Indonesia**, baris 4+ = data.
    Nilai selnya juga memakai `inlineStr`, bukan hanya sharedStrings.
    """
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        shared = ["".join(t.text or "" for t in si.iter(NS + "t"))
                  for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si")]

    raw = []
    for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(NS + "row"):
        cells = {}
        for c in row.findall(NS + "c"):
            col = "".join(ch for ch in (c.get("r") or "") if ch.isalpha())
            cells[col] = _cell_text(c, shared)
        raw.append(cells)

    if len(raw) < 4:
        return []
    # Header di baris ke-3; kolom dgn nama sama (mis. "Nama Variasi 1" muncul 2x)
    # diambil yang PERTAMA saja — kolom yang kita butuhkan semuanya unik.
    header = {}
    for col, name in raw[2].items():
        name = (name or "").strip()
        if name and name not in header:
            header[name] = col

    out = []
    for r in raw[3:]:
        rec = {name: (r.get(col) or "").strip() for name, col in header.items()}
        if rec.get("Kode Produk"):
            out.append(rec)
    return out


def newest(folder, prefix):
    hits = sorted(glob.glob(os.path.join(folder, prefix + "*.xlsx")), key=os.path.getmtime)
    if not hits:
        sys.exit(f"File ekspor '{prefix}*.xlsx' tidak ditemukan di: {folder}\n"
                 f"Ekspor dulu dari Shopee Seller Centre -> Produk Saya -> Mass Update.")
    return hits[-1]


# --------------------------------------------------------------- pembersihan
def clean(s, limit):
    """Rapikan teks untuk feed: satu spasi, tanpa baris baru, dipotong sesuai batas."""
    s = " ".join((s or "").split())
    return s[:limit - 1].rstrip() + "…" if len(s) > limit else s


def to_number(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def brand_of(title):
    """Tentukan merek dari nama produk.

    Tiga lapis, berurutan:
    1. MEREK_DIKENAL — dicocokkan di MANA SAJA dalam judul (bukan hanya di awal),
       supaya "Paket Body & Tail ..." & "Deep Cleanser Body & Tail ..." tetap
       terbaca sebagai Body & Tail. Wajib untuk merek multi-kata, sebab menebak
       dari kata pertama saja menghasilkan "Royal" dan "Happy".
    2. KATA_UMUM — judul yang diawali kata benda generik ("Bowl", "Sisir",
       "Kalung") berarti barang tanpa merek -> pakai nama toko.
    3. Selain itu: kata pertama, pola paling lazim di listing Shopee
       ("Kaniva ...", "Vitagold ...").
    """
    t = (title or "").strip()
    low = t.lower()
    for merek in MEREK_DIKENAL:                 # sudah urut dari yang terpanjang
        if merek.lower() in low:
            return NORMALISASI_MEREK.get(merek, merek)
    first = t.split(" ")[0].strip("-–—,.")
    if first.lower() in KATA_UMUM:
        return BRAND_DEFAULT
    if len(first) >= 3 and any(ch.isalpha() for ch in first) and not first[0].isdigit():
        return first
    return BRAND_DEFAULT


def product_type(kategori):
    """'100908 - Pets/Pet Food/Cat Food' -> 'Pets > Pet Food > Cat Food'."""
    k = (kategori or "").split(" - ", 1)[-1].strip()
    return " > ".join(p.strip() for p in k.split("/") if p.strip())


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Ekspor Shopee -> feed katalog Meta (CSV).")
    ap.add_argument("folder", nargs="?",
                    default=os.path.join(os.path.expanduser("~"), "Downloads"),
                    help="folder berisi file ekspor Shopee (default: Downloads)")
    ap.add_argument("-o", "--out", default=os.path.join("static", "katalog-shopee.csv"),
                    help="file CSV keluaran (default: static/katalog-shopee.csv)")
    args = ap.parse_args()

    f_basic = newest(args.folder, "mass_update_basic_info_")
    f_media = newest(args.folder, "mass_update_media_info_")
    f_sales = newest(args.folder, "mass_update_sales_info_")
    for label, f in (("basic", f_basic), ("media", f_media), ("sales", f_sales)):
        print(f"  {label:6}: {os.path.basename(f)}")

    basic = {r["Kode Produk"]: r for r in read_sheet(f_basic)}
    media = {r["Kode Produk"]: r for r in read_sheet(f_media)}

    # sales_info berisi SATU BARIS PER VARIASI -> kumpulkan per produk.
    sales = {}
    for r in read_sheet(f_sales):
        sales.setdefault(r["Kode Produk"], []).append(r)

    print(f"\nProduk: basic={len(basic)} media={len(media)} sales={len(sales)}")

    rows, lewat = [], []
    for pid, b in basic.items():
        m = media.get(pid, {})
        varian = sales.get(pid, [])

        title = clean(b.get("Nama Produk") or m.get("Nama Produk"), MAX_TITLE)
        image = (m.get("Foto Sampul") or "").strip()
        harga = [h for h in (to_number(v.get("Harga")) for v in varian) if h]

        # Meta menolak entri tanpa judul/gambar/harga -> lebih baik dilewati
        # daripada membuat seluruh feed gagal divalidasi.
        kurang = [n for n, ok in (("judul", title), ("gambar", image), ("harga", harga)) if not ok]
        if kurang:
            lewat.append((pid, title or "(tanpa nama)", ", ".join(kurang)))
            continue

        stok = sum(to_number(v.get("Stok")) or 0 for v in varian)
        extra = [m.get(f"Foto Produk {i}", "").strip() for i in range(1, 9)]
        extra = [u for u in extra if u][:MAX_EXTRA_IMG]

        rows.append({
            "id": pid,
            "title": title,
            "description": clean(b.get("Deskripsi Produk") or title, MAX_DESC),
            # Harga TERENDAH antar variasi — meniru tampilan "mulai dari" di Shopee.
            "price": f"{min(harga):.2f} {CURRENCY}",
            "availability": "in stock" if (ANGGAP_SELALU_TERSEDIA or stok > 0) else "out of stock",
            "condition": "new",
            "link": LINK_TMPL.format(shop=SHOP_ID, item=pid),
            "image_link": image,
            "additional_image_link": ",".join(extra),
            "brand": brand_of(title),
            "product_type": product_type(m.get("Kategori")),
        })

    if not rows:
        sys.exit("Tidak ada produk yang bisa ditulis — periksa file ekspornya.")

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n[OK] {len(rows)} produk -> {out}")
    if lewat:
        print(f"\n{len(lewat)} produk DILEWATI (data wajib tidak lengkap):")
        for pid, nama, alasan in lewat:
            print(f"  - {pid} {nama[:45]} (tidak ada: {alasan})")
    if ANGGAP_SELALU_TERSEDIA:
        habis = sum(1 for pid in basic
                    if sum(to_number(v.get("Stok")) or 0 for v in sales.get(pid, [])) <= 0)
        if habis:
            print(f"\nCatatan: {habis} produk stoknya 0 di Shopee tetapi tetap ditandai "
                  f"'in stock' (sesuai keputusan). Ekspor ulang & jalankan lagi setelah restock.")


if __name__ == "__main__":
    main()
