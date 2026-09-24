/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // explicit imports (describe/it/expect from 'vitest') over injected
    // globals — matches this project's verbatimModuleSyntax convention and
    // needs no tsconfig "types" changes for the production build's tsc -b
    globals: false,
  },
})
