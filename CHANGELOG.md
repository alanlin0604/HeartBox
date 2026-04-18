# Changelog

All notable changes to HeartBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Performance Monitoring**: Added `usePerformance`, `useRenderCount`, and `useWhyDidYouUpdate` hooks for development-mode performance monitoring ([#usePerformance.js](frontend/src/hooks/usePerformance.js))
  - Integrated into DashboardPage, AIChatPage, and AssessmentsPage with 50ms threshold
  - Logs slow renders, tracks re-render counts, and debugs prop changes
  - Comprehensive test coverage (11 tests)
- **Context Testing**: Added comprehensive tests for ToastContext (9 tests) validating all toast methods and API memoization
- **Component Testing**: Expanded test coverage from 20 to 74 tests (+270%)
  - MoodBadge (10 tests)
  - HighlightText (12 tests)
  - ConfirmModal (12 tests)
  - SearchFilterPanel (3 tests)
  - ExportPDFButton (3 tests)
  - EmptyState (3 tests)
- **Offline Support**: Added `OfflineIndicator` component showing network status with user-friendly banners
- **Git Hooks**: Added pre-commit test validation and commit message format enforcement (Conventional Commits)
  - Blocks commits if tests fail
  - Ensures consistent commit message style across the team
- **API Error Handler**: Added centralized error handling utility ([apiErrorHandler.js](frontend/src/utils/apiErrorHandler.js))
  - Status code mapping with i18n support
  - Sentry integration for 500+ errors
  - Configurable silent mode
- **Environment Validation**: Added startup validation for required environment variables ([env.js](frontend/src/config/env.js))
- **PWA Enhancements**:
  - Enhanced manifest.json with lang, dir, scope, id, orientation
  - Added SVG icon support for vector scaling
  - Added third shortcut for AI Chat
  - Added browserconfig.xml for Windows tile support
  - Added iOS-specific meta tags (apple-mobile-web-app-capable, status-bar-style)
  - Added edge_side_panel configuration for Microsoft Edge
  - Added display_override for modern PWA display modes
- **Documentation**:
  - Comprehensive README.md with setup instructions, tech stack, and features
  - CONTRIBUTING.md with code standards and workflow
  - MIT LICENSE
  - .env.example with all required and optional variables documented
  - This CHANGELOG.md

### Fixed
- **Health Data Android**: Implemented Android Health Connect workouts API (was TODO) ([healthKit.js:212-265](frontend/src/services/healthKit.js))
  - Both iOS (HealthKit) and Android (Health Connect) now have complete health data sync
- **TokenStorage Bug**: Fixed null handling in setAccessToken/setRefreshToken causing tests to fail
  - Now properly removes tokens when null/undefined instead of storing "null" string
- **i18n Completeness**: Fixed missing translations in ja.json (health.noData, health.noDataDesc, health.goToSettings)
  - All 3 languages (zh-TW, en, ja) now have complete 1060 keys
- **Security Vulnerabilities**: 
  - Updated dompurify to fix medium-severity XSS vulnerability
  - Updated follow-redirects to fix medium-severity SSRF vulnerability
  - Result: 0 vulnerabilities in both frontend and backend

### Changed
- **Image Optimization**: Converted 11 PNG images to WebP format, reducing size by 56.8% (226.4 KB → 97.8 KB)
  - Updated all image references across 5 files to use .webp
  - Added OptimizedImage component with PNG fallback
- **Performance Optimization**:
  - JournalPage: Wrapped 8 callbacks with useCallback, memoized sidebar content
  - Bundle already optimized with lazy loading and code splitting
  - Recharts (400KB) loaded in separate chunk on demand
- **Test Infrastructure**: 
  - Improved mock implementations for LanguageContext to return actual translations
  - Fixed timing issues in performance hook tests
  - All 74 tests passing consistently

### Deprecated
- None

### Removed
- Duplicate image file (eliminated redundancy in assets)

### Security
- Added environment variable validation to prevent runtime errors from missing config
- Centralized API error handling with Sentry integration for server errors
- All dependencies up-to-date with 0 known vulnerabilities
- Enforced commit message format to maintain clean, auditable git history

---

## [1.0.0-pre-capacitor] - 2024-XX-XX

### Note
Tag `v1.0-pre-capacitor` marks the stable version before Capacitor integration.
See [版本備份與還原指南.md](docs/版本備份與還原指南.md) for details.

---

## Release Conventions

### Version Numbering
- **MAJOR**: Breaking changes (incompatible API changes)
- **MINOR**: New features (backwards-compatible)
- **PATCH**: Bug fixes (backwards-compatible)

### Commit Message Format
We follow [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, perf, test, build, ci, chore

**Examples**:
- `feat(dashboard): add mood calendar widget`
- `fix(auth): handle token refresh race condition`
- `perf(journal): optimize render with useMemo`

---

## Testing
- All changes must pass the test suite (74 tests)
- New features should include tests
- Pre-commit hook automatically runs tests

## Links
- [Project Repository](https://github.com/alanlin0604/HeartBox)
- [Issue Tracker](https://github.com/alanlin0604/HeartBox/issues)
- [Documentation](./docs/)
