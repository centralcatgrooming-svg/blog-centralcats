/* Pengukuran funnel GA4 — klik CTA layanan/booking/WhatsApp & tombol bagikan.
   File ini di-INLINE oleh Hugo (layouts/_default/baseof.html, resources.Get + minify),
   jadi tidak menambah request. Ditulis sebagai skrip klasik (bukan ES module) supaya
   bisa disisipkan apa adanya ke dalam <script>. window.ccAnalytics dipakai oleh test
   Vitest (tests/analytics.test.js).

   KONVENSI NAMA EVENT — dibuat di sini karena repo belum punya aturannya:
   - Nama event & nama parameter: snake_case bahasa Inggris, mengikuti gaya event
     bawaan GA4 (page_view, scroll, click) supaya tidak terlihat asing di laporan.
   - Nilai parameter: bahasa Indonesia huruf kecil — yang membacanya di laporan
     adalah tim Central Cat's.
   - Pakai nama recommended event GA4 apa adanya bila ada padanannya (mis. `share`).
   - SATU NAMA EVENT PER MAKSUD, bukan satu nama + parameter pembeda. Key Event di
     GA4 hanya bisa dipilih berdasar NAMA event, jadi tiap maksud yang mau dijadikan
     konversi wajib punya nama sendiri.

   Event yang dikirim:
     booking_click   tautan ke app.centralcats.id/booking   → kandidat Key Event
     whatsapp_click  tautan wa.me (KONTAK, bukan berbagi)   → kandidat Key Event
     layanan_click   tautan ke centralcats.id/layanan       → kandidat Key Event
     share           tombol di partial share.html           → bukan konversi
*/
(function () {
  'use strict';

  /* Kotak CTA artikel dan footer memakai tautan yang sama persis, jadi tanpa ini
     dua sumber klik yang berbeda arti akan menumpuk jadi satu angka. */
  function ctaLocation(el) {
    if (el.closest('.cc-cta')) return 'cta-artikel';
    if (el.closest('footer.site')) return 'footer';
    if (el.closest('.post')) return 'isi-artikel';
    return 'lainnya';
  }

  /* Metode berbagi diturunkan dari kelas tombol di layouts/partials/share.html. */
  var METHODS = {
    'cc-share__btn--wa': 'whatsapp',
    'cc-share__btn--fb': 'facebook',
    'cc-share__btn--x': 'x',
    'cc-share__btn--tg': 'telegram',
    'cc-share__btn--copy': 'salin-tautan',
    'cc-share__btn--native': 'aplikasi-lain'
  };

  function shareMethod(btn) {
    for (var k in METHODS) {
      if (Object.prototype.hasOwnProperty.call(METHODS, k) && btn.classList.contains(k)) {
        return METHODS[k];
      }
    }
    return 'lainnya';
  }

  /* Pembungkus gtag. Diam saja (tanpa melempar) kalau GA4 diblokir ad-blocker atau
     skrip gtag gagal dimuat — pengukuran tidak boleh merusak halaman.
     transport_type "beacon" penting: CTA artikel TIDAK pakai target="_blank", jadi
     tanpa beacon event bisa hilang saat browser keburu pindah halaman. */
  function send(name, params) {
    if (typeof window.gtag !== 'function') return false;
    var p = { transport_type: 'beacon' };
    for (var k in params) {
      if (Object.prototype.hasOwnProperty.call(params, k)) p[k] = params[k];
    }
    window.gtag('event', name, p);
    return true;
  }

  function handleClick(e) {
    var t = e.target;
    if (!t || !t.closest) return;

    /* Tombol bagikan diperiksa DULUAN. Tombol WhatsApp di dalamnya menuju
       api.whatsapp.com (berbagi artikel), sedangkan kontak toko memakai wa.me.
       Kalau urutannya dibalik, berbagi artikel bisa salah tercatat sebagai lead. */
    var shareBtn = t.closest('.cc-share__btn');
    if (shareBtn) {
      var box = shareBtn.closest('.cc-share');
      send('share', {
        method: shareMethod(shareBtn),
        content_type: 'artikel',
        /* share.html dirender 2x per artikel (top & bottom); dibedakan di sini
           supaya ketahuan posisi mana yang benar-benar dipakai pembaca. */
        variant: box && box.classList.contains('cc-share--bottom') ? 'bottom' : 'top'
      });
      return;
    }

    var a = t.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';

    if (href.indexOf('app.centralcats.id/booking') > -1) {
      send('booking_click', { link_url: href, cta_location: ctaLocation(a) });
    } else if (href.indexOf('wa.me/') > -1) {
      send('whatsapp_click', { link_url: href, cta_location: ctaLocation(a) });
    } else if (href.indexOf('centralcats.id/layanan') > -1) {
      send('layanan_click', { link_url: href, cta_location: ctaLocation(a) });
    }
  }

  function init(root) {
    (root || document).addEventListener('click', handleClick);
  }

  window.ccAnalytics = {
    send: send,
    ctaLocation: ctaLocation,
    shareMethod: shareMethod,
    handleClick: handleClick,
    init: init
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(document); });
  } else {
    init(document);
  }
})();
