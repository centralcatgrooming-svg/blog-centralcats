import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { beforeAll, beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

// Catatan: di environment jsdom, `URL` global adalah milik jsdom — bukan milik Node —
// sehingga new URL(...) tidak bisa disuap ke fileURLToPath. Pakai path saja.
const DIR = dirname(fileURLToPath(import.meta.url))

// assets/js/share.js adalah skrip klasik (bukan ES module) karena di-inline mentah
// oleh Hugo. Jadi di sini ia dievaluasi ke dalam global jsdom, persis seperti di browser.
const SRC = readFileSync(resolve(DIR, '../assets/js/share.js'), 'utf8')

const URL_ARTIKEL = 'https://blog.centralcats.id/kesehatan-hewan/5-tanda-bulu-kucing-sehat/'
const JUDUL = '5 Tanda Bulu Kucing yang Sehat'

function pasangMarkup() {
  document.body.innerHTML = `
    <div class="cc-share cc-share--bottom">
      <div class="cc-share__btns">
        <a class="cc-share__btn cc-share__btn--wa" href="https://api.whatsapp.com/send?text=x">
          <svg></svg><span class="cc-share__nm">WhatsApp</span>
        </a>
        <button type="button" class="cc-share__btn cc-share__btn--copy" data-cc-copy="${URL_ARTIKEL}">
          <svg></svg><span class="cc-share__nm">Salin tautan</span>
        </button>
        <button type="button" class="cc-share__btn cc-share__btn--native" hidden
                data-cc-share-title="${JUDUL}" data-cc-share-url="${URL_ARTIKEL}">
          <svg></svg><span class="cc-share__nm">Lainnya</span>
        </button>
      </div>
    </div>`
}

const q = (sel) => document.querySelector(sel)
const label = (sel) => q(sel).querySelector('.cc-share__nm').textContent

function klik(sel) {
  // Klik pada <svg> di dalam tombol — menguji bahwa closest() naik ke tombolnya.
  const target = q(sel).querySelector('svg') ?? q(sel)
  target.dispatchEvent(new window.MouseEvent('click', { bubbles: true, cancelable: true }))
}

function setNavigator(prop, value) {
  Object.defineProperty(window.navigator, prop, { value, configurable: true, writable: true })
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
  setNavigator('clipboard', undefined)
  setNavigator('share', undefined)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('revealNative', () => {
  it('membiarkan tombol "Lainnya" tersembunyi bila Web Share API tidak ada', () => {
    expect(window.ccShare.revealNative(document)).toBe(0)
    expect(q('.cc-share__btn--native').hidden).toBe(true)
  })

  it('menampilkan tombol "Lainnya" bila browser mendukung Web Share API', () => {
    setNavigator('share', vi.fn())
    expect(window.ccShare.revealNative(document)).toBe(1)
    expect(q('.cc-share__btn--native').hidden).toBe(false)
  })
})

describe('salin tautan', () => {
  it('menyalin permalink lewat Clipboard API di konteks aman', async () => {
    vi.useFakeTimers()
    const writeText = vi.fn().mockResolvedValue(undefined)
    setNavigator('clipboard', { writeText })
    window.isSecureContext = true

    klik('.cc-share__btn--copy')
    await vi.advanceTimersByTimeAsync(0)

    expect(writeText).toHaveBeenCalledWith(URL_ARTIKEL)
    expect(label('.cc-share__btn--copy')).toBe('Tersalin!')
    expect(q('.cc-share__btn--copy').classList.contains('is-done')).toBe(true)
  })

  it('mengembalikan label semula setelah umpan balik selesai', async () => {
    vi.useFakeTimers()
    setNavigator('clipboard', { writeText: vi.fn().mockResolvedValue(undefined) })
    window.isSecureContext = true

    klik('.cc-share__btn--copy')
    await vi.advanceTimersByTimeAsync(1800)

    expect(label('.cc-share__btn--copy')).toBe('Salin tautan')
    expect(q('.cc-share__btn--copy').classList.contains('is-done')).toBe(false)
  })

  it('jatuh ke execCommand bila Clipboard API tidak tersedia', async () => {
    vi.useFakeTimers()
    window.isSecureContext = false
    document.execCommand = vi.fn(() => true)

    klik('.cc-share__btn--copy')
    await vi.advanceTimersByTimeAsync(0)

    expect(document.execCommand).toHaveBeenCalledWith('copy')
    expect(label('.cc-share__btn--copy')).toBe('Tersalin!')
    // textarea sementara harus sudah dibersihkan
    expect(document.querySelector('textarea')).toBeNull()
  })

  it('tidak mengubah label bila penyalinan gagal', async () => {
    vi.useFakeTimers()
    window.isSecureContext = true
    setNavigator('clipboard', { writeText: vi.fn().mockRejectedValue(new Error('ditolak')) })

    klik('.cc-share__btn--copy')
    await vi.advanceTimersByTimeAsync(0)

    expect(label('.cc-share__btn--copy')).toBe('Salin tautan')
  })
})

describe('share native', () => {
  it('meneruskan judul & permalink ke navigator.share', () => {
    const share = vi.fn().mockResolvedValue(undefined)
    setNavigator('share', share)

    klik('.cc-share__btn--native')

    expect(share).toHaveBeenCalledWith({ title: JUDUL, url: URL_ARTIKEL })
  })

  it('tidak melempar error bila pengguna membatalkan share', async () => {
    setNavigator('share', vi.fn().mockRejectedValue(new Error('AbortError')))
    expect(() => klik('.cc-share__btn--native')).not.toThrow()
    await Promise.resolve()
  })
})

describe('tautan share biasa', () => {
  it('klik tombol WhatsApp tidak memicu salin tautan', async () => {
    const writeText = vi.fn()
    setNavigator('clipboard', { writeText })
    window.isSecureContext = true

    klik('.cc-share__btn--wa')
    await Promise.resolve()

    expect(writeText).not.toHaveBeenCalled()
  })
})
