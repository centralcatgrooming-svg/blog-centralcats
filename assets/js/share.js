/* Tombol bagikan artikel — salin tautan + Web Share API.
   File ini di-INLINE oleh Hugo (layouts/_default/baseof.html, resources.Get + minify),
   jadi tidak menambah request. Ditulis sebagai skrip klasik (bukan ES module) supaya
   bisa disisipkan apa adanya ke dalam <script>. window.ccShare dipakai oleh test Vitest
   (tests/share.test.js). */
(function () {
  'use strict';

  /* Salin teks ke clipboard. Pakai Clipboard API bila tersedia & konteks aman,
     selain itu jatuh ke textarea + execCommand (mis. saat dibuka via http lokal). */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy') ? resolve() : reject(new Error('execCommand gagal'));
      } catch (e) {
        reject(e);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  /* Tombol "Lainnya" hanya masuk akal bila browser punya Web Share API (umumnya HP). */
  function revealNative(root) {
    if (!navigator.share) return 0;
    var els = (root || document).querySelectorAll('.cc-share__btn--native');
    for (var i = 0; i < els.length; i++) els[i].hidden = false;
    return els.length;
  }

  /* Ganti label tombol sementara sebagai umpan balik ("Tersalin!"). */
  function flash(btn, msg, ms) {
    var nm = btn.querySelector('.cc-share__nm');
    var old = nm ? nm.textContent : '';
    btn.classList.add('is-done');
    if (nm) nm.textContent = msg;
    setTimeout(function () {
      btn.classList.remove('is-done');
      if (nm) nm.textContent = old;
    }, ms || 1800);
  }

  function handleClick(e) {
    var t = e.target;
    if (!t || !t.closest) return;

    var copyBtn = t.closest('.cc-share__btn--copy');
    if (copyBtn) {
      copyText(copyBtn.getAttribute('data-cc-copy')).then(function () {
        flash(copyBtn, 'Tersalin!');
      }, function () {});
      return;
    }

    var nativeBtn = t.closest('.cc-share__btn--native');
    if (nativeBtn && navigator.share) {
      var p = navigator.share({
        title: nativeBtn.getAttribute('data-cc-share-title'),
        url: nativeBtn.getAttribute('data-cc-share-url')
      });
      /* Batal share = promise reject; jangan biarkan jadi unhandled rejection. */
      if (p && p.catch) p.catch(function () {});
    }
  }

  function init(root) {
    var doc = root || document;
    revealNative(doc);
    doc.addEventListener('click', handleClick);
  }

  window.ccShare = {
    copyText: copyText,
    revealNative: revealNative,
    flash: flash,
    handleClick: handleClick,
    init: init
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(document); });
  } else {
    init(document);
  }
})();
