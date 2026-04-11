import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import compression from 'vite-plugin-compression'
import modulepreloadPlugin from './vite-plugin-modulepreload.js'

const DEV_BACKEND = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    compression({ algorithm: 'gzip' }),
    compression({ algorithm: 'brotliCompress', ext: '.br' }),
    // modulepreloadPlugin(), // Vite already handles modulepreload automatically
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
  build: {
    sourcemap: false,
    reportCompressedSize: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      external: [
        'capacitor-apple-health',
        'capacitor-health-connect',
        '@capacitor/haptics',
      ],
      output: {
        // Better chunk naming for caching
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',

        // Optimized manual chunks with size-based strategy
        manualChunks(id) {
          // Core React libraries
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'vendor-react'
          }
          if (id.includes('node_modules/react-router-dom')) {
            return 'vendor-router'
          }

          // Large visualization library
          if (id.includes('node_modules/recharts')) {
            return 'vendor-recharts'
          }

          // HTTP client
          if (id.includes('node_modules/axios')) {
            return 'vendor-axios'
          }

          // Rich text editor
          if (id.includes('node_modules/@tiptap') || id.includes('node_modules/prosemirror')) {
            return 'vendor-tiptap'
          }

          // Security utilities
          if (id.includes('node_modules/dompurify')) {
            return 'vendor-dompurify'
          }

          // Split other node_modules into a common chunk
          if (id.includes('node_modules')) {
            return 'vendor-common'
          }
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
