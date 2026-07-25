import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.js'],
    // public/ & resources/ = hasil build Hugo, jangan ikut di-scan
    exclude: ['node_modules/**', 'public/**', 'resources/**'],
  },
})
