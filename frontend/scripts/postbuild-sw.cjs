// Stamp the service worker with a fresh CACHE_VERSION on every build so a
// returning user gets the new bundle on the next visit instead of being
// stuck on whatever cache name was hard-coded in source.
//
// Runs as `postbuild` after `vite build`. Replaces the `__CACHE_VERSION__`
// sentinel inside dist/sw.js with `<YYYYMMDDTHHmmss>-<git short sha>`. If
// the substitution can't find the sentinel we exit with a clear message
// instead of silently shipping a SW that won't update.
const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')

const SW_PATH = path.join(__dirname, '..', 'dist', 'sw.js')

function gitSha() {
  try {
    return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString().trim()
  } catch {
    return 'nogit'
  }
}

function timestamp() {
  return new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14)
}

function main() {
  if (!fs.existsSync(SW_PATH)) {
    console.error(`postbuild-sw: ${SW_PATH} not found — did vite build run?`)
    process.exit(1)
  }
  const version = `${timestamp()}-${gitSha()}`
  const before = fs.readFileSync(SW_PATH, 'utf8')
  if (!before.includes('__CACHE_VERSION__')) {
    console.error('postbuild-sw: sentinel __CACHE_VERSION__ missing in sw.js — refusing to ship without versioning')
    process.exit(1)
  }
  const after = before.replace(/__CACHE_VERSION__/g, version)
  fs.writeFileSync(SW_PATH, after, 'utf8')
  console.log(`postbuild-sw: sw.js stamped with version ${version}`)
}

main()
