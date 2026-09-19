/* =============================================================
   Pesan keamanan di console (self-XSS / Social Engineering)
   Ditambahkan 2026-09-19 — menyamakan dengan www.centralcats.id
   dan app.centralcats.id yang sudah punya blok serupa.

   Kenapa ada: modus penipuan "tempelkan kode ini di console" masih
   umum. Peringatan ini muncul tepat di tempat korban akan menempel.

   Tepat 6 pemanggilan console — dijaga tests/konsol-keamanan.test.js.
   Peringatan utamanya sengaja dibuat BANNER bertingkat kontras, bukan
   baris biasa; DevTools hanya mendukung sebagian CSS lewat %c (warna,
   font, background, padding, border) — animation/transition diabaikan,
   jadi efek berkedip memang tidak bisa dibuat di console.

   Di-inline mentah oleh Hugo (resources.Get | minify) di baseof.html,
   jadi ini skrip klasik: jangan pakai import/export.
============================================================= */
console.log(
  "%c  /\_/\\n ( o.o )   Central Cat's\n  > ^ <    Blog Petshop & Grooming Tangerang",
  "color:#d4af37;font-weight:bold;font-size:13px;line-height:1.8;"
);
console.log("%c━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color:#d4af37;font-size:10px;");
console.log("%cHai 👋, kelihatannya kamu membuka Developer Tools.", "color:#60a5fa;font-size:14px;font-weight:600;");
console.log(
  "%c⚠ HARAP BERHATI-HATI SAAT MENEMPELKAN KODE DI SINI ⚠",
  "background:#f59e0b;color:#1a1200;font-size:17px;font-weight:800;padding:12px 18px;border-radius:8px;letter-spacing:.4px;border:2px solid #b45309;"
);
console.log("%cJika seseorang menyuruhmu menempelkan sesuatu di console,\nbisa jadi itu adalah penipuan (Social Engineering Attack).", "color:#ef4444;font-size:13px;");
console.log("%cBlog Central Cat's  •  https://blog.centralcats.id", "color:#22c55e;font-size:13px;font-weight:600;");
