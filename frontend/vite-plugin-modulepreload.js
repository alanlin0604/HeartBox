/**
 * Vite Plugin: Auto-inject modulepreload for critical vendor chunks
 *
 * This plugin automatically adds <link rel="modulepreload"> tags to index.html
 * for critical vendor chunks (react, router, common) to speed up initial load.
 */

export default function modulepreloadPlugin() {
  return {
    name: 'vite-plugin-modulepreload',
    apply: 'build',

    transformIndexHtml: {
      order: 'post',
      handler(html, ctx) {
        // Safely access bundle
        if (!ctx || !ctx.bundle) {
          return html
        }

        // Extract all JS chunks from the bundle
        const chunks = Object.keys(ctx.bundle)
          .filter(name => name.endsWith('.js'))
          .filter(name => {
            // Only preload critical vendor chunks
            return name.includes('vendor-react') ||
                   name.includes('vendor-router') ||
                   name.includes('vendor-common') ||
                   name.includes('index-')
          })

        if (chunks.length === 0) return html

        // Generate modulepreload tags
        const preloadTags = chunks
          .map(chunk => {
            // Chunk already includes 'assets/' prefix, so just prepend '/'
            const path = `/${chunk}`
            return `    <link rel="modulepreload" href="${path}" crossorigin />`
          })
          .join('\n')

        // Inject before closing </head>
        return html.replace('</head>', `${preloadTags}\n  </head>`)
      }
    }
  }
}
