import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import compression from 'vite-plugin-compression'
import { visualizer } from 'rollup-plugin-visualizer'
import { execSync } from 'child_process'
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const DEV_BACKEND = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

// Generate cache version from git commit hash + build timestamp
function getCacheVersion() {
  try {
    const gitHash = execSync('git rev-parse --short HEAD').toString().trim()
    const timestamp = new Date().toISOString().replace(/[:-]/g, '').slice(0, 15)
    return `v${timestamp}-${gitHash}`
  } catch {
    // Fallback if git is not available
    return `v${Date.now()}`
  }
}

// Custom plugin to inject cache version into service worker
function injectSWVersion() {
  return {
    name: 'inject-sw-version',
    apply: 'build',
    writeBundle() {
      const swPath = join(__dirname, 'dist', 'sw.js')

      if (existsSync(swPath)) {
        let swContent = readFileSync(swPath, 'utf-8')
        const cacheVersion = getCacheVersion()

        // Replace hardcoded version with generated version
        swContent = swContent.replace(
          /const CACHE_NAME = 'heartbox-cache-v\d+'/,
          `const CACHE_NAME = 'heartbox-cache-${cacheVersion}'`
        )
        swContent = swContent.replace(
          /const STATIC_CACHE = 'heartbox-static-v\d+'/,
          `const STATIC_CACHE = 'heartbox-static-${cacheVersion}'`
        )
        swContent = swContent.replace(
          /const IMAGE_CACHE = 'heartbox-images-v\d+'/,
          `const IMAGE_CACHE = 'heartbox-images-${cacheVersion}'`
        )
        swContent = swContent.replace(
          /const FONT_CACHE = 'heartbox-fonts-v\d+'/,
          `const FONT_CACHE = 'heartbox-fonts-${cacheVersion}'`
        )

        writeFileSync(swPath, swContent)
        console.log(`✅ Service Worker version updated to: ${cacheVersion}`)
      }
    },
  }
}

export default defineConfig({
  define: {
    __CACHE_VERSION__: JSON.stringify(getCacheVersion()),
  },
  plugins: [
    react(),
    tailwindcss(),
    injectSWVersion(),
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
          // Recharts auto-splits per chart type (BarChart/LineChart/etc.)
          'vendor-axios': ['axios'],
          // DOMPurify lives in the same lazy chunks as Tiptap (RichTextEditor)
          // and the dangerouslySetInnerHTML callers — merging avoids a second
          // network round-trip when those pages first open.
          'vendor-tiptap': [
            '@tiptap/react',
            '@tiptap/starter-kit',
            '@tiptap/extension-placeholder',
            'dompurify',
          ],
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
