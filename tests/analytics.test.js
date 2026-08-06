import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { beforeAll, beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

// Catatan: di environment jsdom, `URL` global adalah milik jsdom — bukan milik Node —
// sehingga new URL(...) tidak bisa disuap ke fileURLToPath. Pakai path saja.
const DIR = dirname(fileURLToPath(import.meta.url))

// assets/js/analytics.js adalah skrip klasik (bukan ES module) karena di-inline mentah
// oleh Hugo. Jadi di sini ia dievaluasi ke dalam global jsdom, persis seperti di browser.
const SRC = readFileSync(resolve(DIR, '../assets/js/analytics.js'), 'utf8')

const BOOKING = 'https://app.centralcats.id/booking'
const LAYANAN = 'https://www.centralcats.id/layanan'
const WA_KONTAK = 'https://wa.me/6282111827798'
const WA_SHARE = 'https://api.whatsapp.com/send?text=Judul%20Artikel'

function pasangMarkup() {
  // Meniru struktur nyata: single.html (artikel + share 2 varian + kotak CTA)
  // dan footer di baseof.html.
  document.body.innerHTML = `
    <article class="post">
      <div class="cc-share cc-share--top">
        <div class="cc-share__btns">
          <a class="cc-share__btn cc-share__btn--wa" href="${WA_SHARE}">
            <svg></svg><span class="cc-share__nm">WhatsApp</span>
          </a>
        </div>
      </div>
      <div class="cc-share cc-share--bottom">
        <div class="cc-share__btns">
          <a class="cc-share__btn cc-share__btn--tg" href="https://t.me/share/url?url=x">
            <svg></svg><span class="cc-share__nm">Telegram</span>
          </a>
          <button type="button" class="cc-share__btn cc-share__btn--copy" data-cc-copy="x">
            <svg></svg><span class="cc-share__nm">Salin tautan</span>
          </button>
        </div>
      </div>
      <aside class="cc-cta">
        <div class="cc-cta__btns">
          <a class="cc-cta__btn cc-cta__btn--primary" href="${LAYANAN}">Lihat Layanan</a>
          <a class="cc-cta__btn" href="${BOOKING}">Booking Sekarang</a>
        </div>
      </aside>
      <p><a class="tautan-isi" href="${BOOKING}">booking di tengah artikel</a></p>
    </article>
    <footer class="site">
      <a class="wa-footer" href="${WA_KONTAK}">WhatsApp: 0821-1182-7798</a>
      <a class="lain" href="/kesehatan-hewan/">Kesehatan Hewan</a>
    </footer>`
}

const q = (sel) => document.querySelector(sel)

function klik(sel) {
  // Klik pada <svg> di dalam tombol bila ada — menguji bahwa closest() naik ke tombolnya.
  const target = q(sel).querySelector('svg') ?? q(sel)
  target.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }))
}

// Event terakhir yang dikirim ke gtag, sebagai { name, params }.
function terkirim() {
  const calls = window.gtag.mock.calls
  const last = calls[calls.length - 1]
  return { name: last[1], params: last[2] }
}

beforeAll(() => {
  // Cegah jsdom mencoba navigasi saat <a> diklik (bikin log "Not implemented").
  document.addEventListener('click', (e) => {
    if (e.target.closest?.('a[href]')) e.preventDefault()
  })
  new Function(SRC)() // sekali saja: skrip memasang listener delegasi di document
})

beforeEach(() => {
  pasangMarkup()
  window.gtag = vi.fn()
})

afterEach(() => {
  vi.restoreAllMocks()
  delete window.gtag
})

describe('send', () => {
  it('mengirim event ke gtag dengan transport_type beacon', () => {
    expect(window.ccAnalytics.send('uji', { a: 1 })).toBe(true)
    expect(window.gtag).toHaveBeenCalledWith('event', 'uji', { transport_type: 'beacon', a: 1 })
  })

  it('tidak melempar error bila gtag tidak ada (mis. diblokir ad-blocker)', () => {
    delete window.gtag
    expect(() => window.ccAnalytics.send('uji', {})).not.toThrow()
    expect(window.ccAnalytics.send('uji', {})).toBe(false)
  })

  it('tidak mengubah objek parameter milik pemanggil', () => {
    const params = { a: 1 }
    window.ccAnalytics.send('uji', params)
    expect(params).toEqual({ a: 1 })
  })
})

describe('klik CTA', () => {
  it('mencatat booking_click dari kotak CTA artikel', () => {
    klik('.cc-cta__btn:not(.cc-cta__btn--primary)')
    expect(terkirim()).toEqual({
      name: 'booking_click',
      params: { transport_type: 'beacon', link_url: BOOKING, cta_location: 'cta-artikel' }
    })
  })

  it('mencatat layanan_click dari kotak CTA artikel', () => {
    klik('.cc-cta__btn--primary')
    expect(terkirim()).toEqual({
      name: 'layanan_click',
      params: { transport_type: 'beacon', link_url: LAYANAN, cta_location: 'cta-artikel' }
    })
  })

  it('membedakan booking di dalam isi artikel dari yang di kotak CTA', () => {
    klik('.tautan-isi')
    expect(terkirim().params.cta_location).toBe('isi-artikel')
  })

  it('mencatat whatsapp_click dari footer', () => {
    klik('.wa-footer')
    expect(terkirim()).toEqual({
      name: 'whatsapp_click',
      params: { transport_type: 'beacon', link_url: WA_KONTAK, cta_location: 'footer' }
    })
  })

  it('mengabaikan tautan biasa yang bukan CTA', () => {
    klik('.lain')
    expect(window.gtag).not.toHaveBeenCalled()
  })
})

describe('tombol bagikan', () => {
  it('mencatat event share, bukan whatsapp_click, saat berbagi ke WhatsApp', () => {
    // Regresi terpenting: tombol ini menuju api.whatsapp.com (berbagi artikel),
    // bukan wa.me (kontak toko). Salah klasifikasi = angka lead ikut naik palsu.
    klik('.cc-share__btn--wa')
    const { name, params } = terkirim()
    expect(name).toBe('share')
    expect(params.method).toBe('whatsapp')
    expect(window.gtag).toHaveBeenCalledTimes(1)
  })

  it('membedakan varian top dan bottom', () => {
    klik('.cc-share--top .cc-share__btn--wa')
    expect(terkirim().params.variant).toBe('top')

    klik('.cc-share--bottom .cc-share__btn--tg')
    expect(terkirim().params.variant).toBe('bottom')
  })

  it('mencatat tombol salin tautan sebagai metode salin-tautan', () => {
    klik('.cc-share__btn--copy')
    expect(terkirim()).toEqual({
      name: 'share',
      params: {
        transport_type: 'beacon',
        method: 'salin-tautan',
        content_type: 'artikel',
        variant: 'bottom'
      }
    })
  })

  it('shareMethod jatuh ke "lainnya" untuk kelas tombol yang tak dikenal', () => {
    const btn = document.createElement('button')
    btn.className = 'cc-share__btn cc-share__btn--entah'
    expect(window.ccAnalytics.shareMethod(btn)).toBe('lainnya')
  })
})
