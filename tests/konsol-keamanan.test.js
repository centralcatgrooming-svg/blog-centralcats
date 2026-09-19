import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// Pesan keamanan console (self-XSS). Ditambahkan 2026-09-19 supaya blog setara
// dengan www.centralcats.id dan app.centralcats.id yang sudah punya blok ini.
// Modus "tempelkan kode ini di console" masih umum; peringatannya harus muncul
// tepat di tempat korban akan menempel. Jadi blok ini FITUR, bukan sisa debug --
// tes ini yang mencegahnya ikut terbuang saat bersih-bersih console.
const DIR = dirname(fileURLToPath(import.meta.url))
const SRC = readFileSync(resolve(DIR, '../assets/js/konsol-keamanan.js'), 'utf8')
const BASEOF = readFileSync(resolve(DIR, '../layouts/_default/baseof.html'), 'utf8')

describe('Pesan keamanan console (fitur disengaja, jangan dihapus)', () => {
  let spy
  beforeEach(() => { spy = vi.spyOn(console, 'log').mockImplementation(() => {}) })
  afterEach(() => { spy.mockRestore() })

  it('menghasilkan tepat 6 pesan saat dijalankan', () => {
    // Skrip klasik (di-inline mentah oleh Hugo), jadi dievaluasi apa adanya.
    new Function(SRC)()
    expect(spy).toHaveBeenCalledTimes(6)
  })

  it('memuat peringatan self-XSS yang jadi inti blok ini', () => {
    new Function(SRC)()
    const semua = spy.mock.calls.flat().join(' ')
    expect(semua).toMatch(/HARAP BERHATI-HATI SAAT MENEMPELKAN KODE/i)
    expect(semua).toMatch(/Social Engineering Attack/i)
  })

  // Escaping ASCII art gampang hilang satu backslash saat berkas ditulis lewat
  // shell/heredoc. Akibatnya string memuat teks '\\n' alih-alih baris baru dan
  // gambar kucingnya berantakan -- tidak ada yang merah, hanya jelek di console.
  // Sudah kejadian 2026-09-19, jadi dikunci di sini.
  it('ASCII art tercetak sebagai 3 baris, bukan teks escape mentah', () => {
    new Function(SRC)()
    const pertama = String(spy.mock.calls[0][0]).replace(/^%c/, '')
    expect(pertama).not.toContain('\\n')
    expect(pertama.split('\n')).toHaveLength(3)
    expect(pertama).toContain('( o.o )')
  })

  it('di-inline oleh baseof.html', () => {
    // Kalau barisnya hilang dari template, skripnya tidak pernah jalan di
    // browser walau berkasnya masih ada -- gagal diam-diam tanpa tes ini.
    expect(BASEOF).toContain('js/konsol-keamanan.js')
  })
})

describe('Tema blog: default terang, tidak ikut OS', () => {
  // Keputusan user 2026-09-19, disamakan dengan situs utama. Sebelumnya script
  // anti-kedip menanyakan skema warna OS, jadi pengunjung ber-OS gelap melihat
  // blog gelap tanpa pernah menekan tombol tema.
  const kode = BASEOF.replace(/<!--[\s\S]*?-->/g, '')

  it('script anti-kedip tidak menanyakan skema warna OS', () => {
    expect(kode).not.toMatch(/prefers-color-scheme/i)
  })

  it('default data-theme adalah light', () => {
    expect(kode).toContain("localStorage.getItem('theme')==='dark'?'dark':'light'")
  })
})

describe('Lebar artikel sejajar dengan header', () => {
  // Keputusan user 2026-09-19. Cangkang situs (.topbar/.wrap/.footer-inner)
  // semuanya 1100px dan halaman utama sudah sejajar; hanya article.post yang
  // menyimpang di 760px, sehingga isi artikel masuk 150px ke dalam dibanding
  // tepi logo/nav. Nilai 1100 pada article.post efektif jadi 1060px karena
  // dipotong padding .wrap -- dan 1060 itu persis isi header.
  // Kalau angka cangkangnya diubah, angka artikel WAJIB ikut; keduanya dikunci
  // bersama di sini. Sengaja TANPA regex ber-escape: berkas ini pernah rusak
  // gara-gara backslash hilang saat ditulis lewat shell.
  const nilai = (sel) => {
    const i = BASEOF.indexOf(sel + '{')
    if (i < 0) return null
    const blok = BASEOF.slice(i, BASEOF.indexOf('}', i))
    const j = blok.indexOf('max-width:')
    if (j < 0) return null
    return parseInt(blok.slice(j + 'max-width:'.length), 10)
  }

  it('article.post selebar cangkang situs', () => {
    expect(nilai('article.post')).toBe(nilai('.wrap'))
  })

  it('cangkang situs masih 1100px', () => {
    expect(nilai('.wrap')).toBe(1100)
    expect(nilai('.topbar')).toBe(1100)
  })
})
