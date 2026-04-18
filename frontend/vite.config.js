import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import compression from 'vite-plugin-compression'
import { visualizer } from 'rollup-plugin-visualizer'

const DEV_BACKEND = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    compression({ algorithm: 'gzip' }),
    visualizer({
      filename: './dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
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
    minify: 'terser',
    cssMinify: true,
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug'],
        passes: 2,
      },
      mangle: {
        safari10: true,
      },
      format: {
        comments: false,
      },
    },
    cssCodeSplit: true,
    assetsInlineLimit: 4096,
    rollupOptions: {
      external: [
        'capacitor-apple-health',
        'capacitor-health-connect',
      ],
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // Remove recharts from manualChunks to enable automatic code splitting per chart type
          // Each chart component (Bar, Line, Scatter, Radar) will be split into separate chunks
          'vendor-axios': ['axios'],
          'vendor-tiptap': ['@tiptap/react', '@tiptap/starter-kit', '@tiptap/extension-placeholder'],
          'vendor-dompurify': ['dompurify'],
          'vendor-framer': ['framer-motion'],
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
