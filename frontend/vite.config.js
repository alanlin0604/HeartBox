import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import compression from 'vite-plugin-compression'

const DEV_BACKEND = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss(), compression({ algorithm: 'gzip' })],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-recharts': ['recharts'],
          'vendor-axios': ['axios'],
          'vendor-tiptap': ['@tiptap/react', '@tiptap/starter-kit'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: DEV_BACKEND,
        changeOrigin: true,
      },
      '/ws': {
        target: DEV_BACKEND,
        changeOrigin: true,
        ws: true,
      },
      '/media': {
        target: DEV_BACKEND,
        changeOrigin: true,
      },
    },
  },
})
