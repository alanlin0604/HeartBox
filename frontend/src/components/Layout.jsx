import { useState, useRef, useEffect, lazy, Suspense } from 'react'
import { NavLink, Outlet, useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import { LANG_OPTIONS } from '../utils/locales'
import NotificationBell from './NotificationBell'
import useIdleTimer from '../hooks/useIdleTimer'
import useGlobalHealthSync from '../hooks/useGlobalHealthSync'
import { useToast } from '../context/ToastContext'

// OnboardingModal only renders for users who haven't completed onboarding,
// so it lives in its own chunk and only downloads when actually shown.
const OnboardingModal = lazy(() => import('./OnboardingModal'))

const ROUTE_PRELOADS = {
  '/': () => import('../pages/JournalPage'),
  '/dashboard': () => import('../pages/DashboardPage'),
  // /personal-dashboard removed 2026-05-19; no preload needed.
  // '/counselors': () => import('../pages/CounselorListPage'), // hidden pre-launch
  '/ai-chat': () => import('../pages/AIChatPage'),
  '/achievements': () => import('../pages/AchievementsPage'),
  '/assessments': () => import('../pages/AssessmentsPage'),
  '/weekly-summary': () => import('../pages/WeeklySummaryPage'),
  '/learn': () => import('../pages/PsychoContentPage'),
  '/admin': () => import('../pages/AdminPage'),
  '/settings': () => import('../pages/SettingsPage'),
  '/guide': () => import('../pages/GuidePage'),
  '/habits': () => import('../pages/HabitsPage'),
  '/friends': () => import('../pages/FriendsPage'),
}

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { lang, setLang, t } = useLang()
  const toast = useToast()
  const [resending, setResending] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const isChatRoute = location.pathname.startsWith('/chat/') || location.pathname === '/ai-chat'
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const menuRef = useRef(null)

  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef(null)
  // Desktop group dropdowns — track which is open (one at a time).
  // hoverCloseTimer cushions the cursor traverse between trigger and panel
  // so a brief gap doesn't flicker the dropdown closed.
  const [openGroupId, setOpenGroupId] = useState(null)
  const hoverCloseTimerRef = useRef(null)
  const desktopGroupsRef = useRef(null)

  const idleTimeout = parseInt(localStorage.getItem('heartbox_idle_timeout') || '30', 10)
  const idleEnabled = idleTimeout > 0

  const { showWarning: idleWarning, countdown: idleCountdown, dismissWarning: dismissIdle } = useIdleTimer({
    timeout: idleTimeout * 60 * 1000,
    onIdle: () => { logout(); navigate('/login') },
    enabled: idleEnabled,
  })

  // Sync health data on cold start + every app foreground (no-op on web)
  useGlobalHealthSync()

  const [onboardingDone, setOnboardingDone] = useState(true)
  useEffect(() => {
    if (user && user.onboarding_completed === false) {
      setOnboardingDone(false)
    }
  }, [user])

  // Close both dropdowns on outside click (single listener)
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
      if (moreRef.current && !moreRef.current.contains(e.target)) {
        setMoreOpen(false)
      }
      if (desktopGroupsRef.current && !desktopGroupsRef.current.contains(e.target)) {
        setOpenGroupId(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Online/offline listener
  useEffect(() => {
    const goOnline = () => setIsOffline(false)
    const goOffline = () => setIsOffline(true)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  // Font scale from localStorage
  useEffect(() => {
    const scale = localStorage.getItem('heartbox_font_scale') || '1'
    document.documentElement.style.fontSize = parseFloat(scale) * 16 + 'px'
  }, [])

  // Single high-traffic route shown standalone on desktop.
  const journalLink = { to: '/', label: t('nav.journal'), icon: '/icons/日誌.webp', end: true }

  // Desktop dropdown groups — hover to expand. Each group's `routes`
  // becomes a vertical menu panel under the trigger.
  const desktopGroups = [
    {
      id: 'analytics',
      label: t('nav.group.analytics'),
      routes: [
        { to: '/dashboard', label: t('nav.dashboard'), icon: '/icons/心情週報月報.webp' },
        // /personal-dashboard removed 2026-05-19 — redundant with /dashboard.
        { to: '/weekly-summary', label: t('nav.weeklySummary'), icon: '/icons/每週報告.webp' },
        { to: '/assessments', label: t('nav.assessments'), icon: '/icons/問卷評估.webp' },
      ],
    },
    {
      id: 'health',
      label: t('nav.group.health'),
      routes: [
        { to: '/habits', label: t('nav.habits'), icon: '/icons/habit.svg' },
        { to: '/sleep-analysis', label: t('nav.sleepAnalysis'), icon: '/icons/sleep.svg' },
        { to: '/breathe', label: t('nav.breathe'), icon: '/icons/呼吸與冥想.webp' },
      ],
    },
    {
      id: 'social',
      label: t('nav.group.social'),
      routes: [
        { to: '/friends', label: t('friends.title'), icon: '/icons/friends.svg' },
        { to: '/community', label: t('nav.community'), icon: '/icons/anonymous.svg' },
        { to: '/ai-chat', label: t('nav.aiChat'), icon: '/icons/AI 聊天.webp' },
        // /counselors hidden pre-launch — no approved counselors yet.
      ],
    },
    {
      id: 'more',
      label: t('nav.more'),
      routes: [
        { to: '/learn', label: t('nav.learn'), icon: '/icons/學習.webp' },
        { to: '/achievements', label: t('nav.achievements'), icon: '/icons/成就.webp' },
        { to: '/import', label: t('nav.dataImport'), icon: '/icons/import.svg' },
        { to: '/guide', label: t('nav.guide'), icon: '/icons/功能指南.webp' },
      ],
    },
  ]

  // Flattened list still used for mobile bottom nav + mobile More + slide-down menu.
  const navLinks = [
    journalLink,
    { to: '/dashboard', label: t('nav.dashboard'), icon: '/icons/心情週報月報.webp' },
    { to: '/habits', label: t('nav.habits'), icon: '/icons/habit.svg' },
    { to: '/ai-chat', label: t('nav.aiChat'), icon: '/icons/AI 聊天.webp' },
    // /personal-dashboard removed 2026-05-19 — redundant with /dashboard.
    { to: '/friends', label: t('friends.title'), icon: '/icons/friends.svg' },
    // /counselors hidden pre-launch
    { to: '/assessments', label: t('nav.assessments'), icon: '/icons/問卷評估.webp' },
    { to: '/weekly-summary', label: t('nav.weeklySummary'), icon: '/icons/每週報告.webp' },
    { to: '/sleep-analysis', label: t('nav.sleepAnalysis'), icon: '/icons/sleep.svg' },
    { to: '/community', label: t('nav.community'), icon: '/icons/anonymous.svg' },
    { to: '/breathe', label: t('nav.breathe'), icon: '/icons/呼吸與冥想.webp' },
    { to: '/learn', label: t('nav.learn'), icon: '/icons/學習.webp' },
    { to: '/achievements', label: t('nav.achievements'), icon: '/icons/成就.webp' },
    { to: '/import', label: t('nav.dataImport'), icon: '/icons/import.svg' },
    { to: '/guide', label: t('nav.guide'), icon: '/icons/功能指南.webp' },
  ]

  // Mobile bottom: first 4 + More dropdown holding the rest.
  const bottomNavLinks = navLinks.slice(0, 4)
  const moreNavLinks = navLinks.slice(4)

  // Hover-to-open with delayed close prevents flicker as the cursor moves
  // from the trigger into the dropdown panel.
  const openGroup = (id) => {
    if (hoverCloseTimerRef.current) {
      clearTimeout(hoverCloseTimerRef.current)
      hoverCloseTimerRef.current = null
    }
    setOpenGroupId(id)
  }
  const scheduleCloseGroup = () => {
    if (hoverCloseTimerRef.current) clearTimeout(hoverCloseTimerRef.current)
    hoverCloseTimerRef.current = setTimeout(() => setOpenGroupId(null), 150)
  }

  return (
    <div
      className={`flex flex-col ${isChatRoute ? 'overflow-hidden' : 'min-h-screen'}`}
      style={isChatRoute ? {
        // body has padding-top/bottom = env(safe-area-inset-*); h-dvh ignored
        // those, so the wrapper extended past the viewport and squeezed the
        // chat header up under the sticky nav. Subtract them explicitly.
        height: 'calc(100dvh - env(safe-area-inset-top) - env(safe-area-inset-bottom))',
      } : undefined}
    >
      {/* Skip to main content link for accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-orange-600 focus:text-white focus:rounded-lg focus:text-sm"
      >
        {t('aria.skipToContent')}
      </a>

      {/* Offline banner */}
      {isOffline && (
        <div className="bg-yellow-500/90 text-black text-center text-sm py-1.5 px-4 font-medium">
          {t('common.offline')}
        </div>
      )}

      {/* Email not verified banner */}
      {user && user.email_verified === false && (
        <div className="bg-yellow-500/80 text-black text-center text-sm py-1.5 px-4 font-medium">
          {t('email.notVerifiedBanner')}
          <button
            onClick={async () => {
              if (resending) return
              setResending(true)
              try {
                const { resendVerification } = await import('../api/auth')
                await resendVerification()
                toast?.success(t('email.resendSuccess'))
              } catch {
                toast?.error(t('email.resendFailed'))
              } finally {
                setResending(false)
              }
            }}
            disabled={resending}
            className="underline ml-2 font-semibold"
          >
            {resending ? t('common.loading') : t('email.resendVerification')}
          </button>
        </div>
      )}

      <nav
        className="nav-bar sticky z-50 mx-4 mt-4 px-6 py-3 flex items-center justify-between"
        style={{ top: 'env(safe-area-inset-top)' }}
      >
        <h1 className="text-xl font-bold bg-gradient-to-r from-orange-500 to-rose-500 bg-clip-text text-transparent flex items-center gap-2 flex-shrink-0">
          <img src="/logo.png" alt="HeartBox" decoding="async" className="w-12 h-12 object-contain" />
          {t('app.displayName')}
        </h1>

        {/* Mobile: notification bell + hamburger (always visible) */}
        <div className="md:hidden flex items-center gap-3">
          <NotificationBell />
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="opacity-70 hover:opacity-100 transition-opacity cursor-pointer p-2 -mr-2"
            aria-label={t('aria.toggleMenu')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {mobileNavOpen ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </>
              ) : (
                <>
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </>
              )}
            </svg>
          </button>
        </div>

        {/* Desktop nav */}
        <div ref={desktopGroupsRef} className="hidden md:flex items-center gap-3 lg:gap-5 xl:gap-6 text-sm lg:text-base flex-shrink min-w-0">
          {/* Journal — high-traffic, kept as standalone link */}
          <NavLink
            to={journalLink.to}
            end={journalLink.end}
            onMouseEnter={() => ROUTE_PRELOADS[journalLink.to]?.()}
            className={({ isActive }) =>
              `font-medium transition-colors flex items-center gap-1 whitespace-nowrap ${isActive ? 'text-orange-500' : 'opacity-60 hover:opacity-100'}`
            }
          >
            <img src={journalLink.icon} alt="" className="w-6 h-6 lg:w-7 lg:h-7 object-contain flex-shrink-0" />
            {journalLink.label}
          </NavLink>

          {/* 4 grouped dropdowns: 分析 / 健康 / 社群 / 更多 */}
          {desktopGroups.map((group) => {
            const isOpen = openGroupId === group.id
            const hasActiveChild = group.routes.some((r) => location.pathname === r.to)
            return (
              <div
                key={group.id}
                className="relative"
                onMouseEnter={() => openGroup(group.id)}
                onMouseLeave={scheduleCloseGroup}
              >
                <button
                  type="button"
                  onClick={() => setOpenGroupId(isOpen ? null : group.id)}
                  aria-haspopup="menu"
                  aria-expanded={isOpen}
                  className={`font-medium transition-colors flex items-center gap-1 whitespace-nowrap cursor-pointer py-1 ${
                    isOpen || hasActiveChild ? 'text-orange-500' : 'opacity-60 hover:opacity-100'
                  }`}
                >
                  {group.label}
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}>
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                {isOpen && (
                  <div
                    role="menu"
                    className="absolute left-0 top-full pt-2 z-50 min-w-[14rem]"
                  >
                    <div className="rounded-xl shadow-xl border border-[var(--card-border)] bg-[var(--tooltip-bg)] py-2">
                      {group.routes.map((link) => (
                        <NavLink
                          key={link.to}
                          to={link.to}
                          end={link.end}
                          onClick={() => setOpenGroupId(null)}
                          onMouseEnter={() => ROUTE_PRELOADS[link.to]?.()}
                          className={({ isActive }) =>
                            `px-4 py-2.5 text-sm transition-colors flex items-center gap-2.5 ${isActive ? 'text-orange-500' : 'opacity-70 hover:opacity-100 hover:bg-orange-500/10'}`
                          }
                        >
                          <img src={link.icon} alt="" className="w-6 h-6 object-contain flex-shrink-0" />
                          {link.label}
                        </NavLink>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {user?.is_staff && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `font-medium transition-colors ${isActive ? 'text-orange-500' : 'opacity-60 hover:opacity-100'}`
              }
            >
              {t('nav.admin')}
            </NavLink>
          )}
          <NotificationBell />

          {/* User dropdown */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center gap-1.5 opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
            >
              {user?.avatar ? (
                <img src={user.avatar} alt={user.username} loading="lazy" decoding="async" className="w-7 h-7 rounded-full object-cover border border-white/20" />
              ) : (
                <span className="w-7 h-7 rounded-full bg-orange-500/25 text-xs flex items-center justify-center">
                  {user?.username?.slice(0, 1)?.toUpperCase()}
                </span>
              )}
              <span className="font-medium">{user?.username}</span>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`transition-transform ${menuOpen ? 'rotate-180' : ''}`}
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-8 w-56 rounded-xl shadow-xl z-50 border border-[var(--card-border)] bg-[var(--tooltip-bg)] py-2">
                {/* Settings */}
                <button
                  onClick={() => { navigate('/settings'); setMenuOpen(false) }}
                  className="w-full text-left px-4 py-2.5 text-sm hover:bg-orange-500/10 transition-colors cursor-pointer flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                  {t('settings.title')}
                </button>

                {/* Theme toggle */}
                <button
                  onClick={() => { toggleTheme(); setMenuOpen(false) }}
                  className="w-full text-left px-4 py-2.5 text-sm hover:bg-orange-500/10 transition-colors cursor-pointer flex items-center gap-2"
                  aria-label={theme === 'dark' ? t('aria.switchToLight') : t('aria.switchToDark')}
                >
                  <span className="text-base w-4 text-center">{theme === 'dark' ? '☀️' : '🌙'}</span>
                  {theme === 'dark' ? t('nav.themeLight') : t('nav.themeDark')}
                </button>

                {/* Language */}
                <div className="px-4 py-2.5 flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                  <div className="flex items-center gap-1">
                    {LANG_OPTIONS.map((opt) => (
                      <button
                        key={opt.code}
                        onClick={() => { setLang(opt.code); setMenuOpen(false) }}
                        className={`px-2 py-0.5 text-xs rounded cursor-pointer transition-all ${
                          lang === opt.code
                            ? 'bg-orange-500/30 text-orange-500 font-bold'
                            : 'opacity-50 hover:opacity-100'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="border-t border-[var(--card-border)] my-1" />

                {/* Logout */}
                <button
                  onClick={() => { logout(); setMenuOpen(false) }}
                  className="w-full text-left px-4 py-2.5 text-sm hover:bg-red-500/10 text-red-500 transition-colors cursor-pointer flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  {t('nav.logout')}
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile nav dropdown */}
      {mobileNavOpen && (
        <div className="md:hidden nav-bar mx-4 mt-2 p-4 space-y-3 z-40">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={() => setMobileNavOpen(false)}
              className={({ isActive }) =>
                `block font-medium transition-colors py-1 flex items-center gap-2 ${isActive ? 'text-orange-500' : 'opacity-60 hover:opacity-100'}`
              }
            >
              <img src={link.icon} alt="" className="w-7 h-7 object-contain" />
              {link.label}
            </NavLink>
          ))}
          {user?.is_staff && (
            <NavLink
              to="/admin"
              onClick={() => setMobileNavOpen(false)}
              className={({ isActive }) =>
                `block font-medium transition-colors py-1 ${isActive ? 'text-orange-500' : 'opacity-60 hover:opacity-100'}`
              }
            >
              {t('nav.admin')}
            </NavLink>
          )}
          <div className="border-t border-[var(--card-border)] pt-3 space-y-3">
            {/* Language picker (mobile) — desktop has its own in the user dropdown */}
            <div className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              <div className="flex items-center gap-1">
                {LANG_OPTIONS.map((opt) => (
                  <button
                    key={opt.code}
                    onClick={() => { setLang(opt.code); setMobileNavOpen(false) }}
                    className={`px-2 py-1 text-xs rounded transition-all ${
                      lang === opt.code
                        ? 'bg-orange-500/30 text-orange-500 font-bold'
                        : 'opacity-50 hover:opacity-100'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => { navigate('/settings'); setMobileNavOpen(false) }}
                className="text-sm opacity-60 hover:opacity-100"
              >
                {t('settings.title')}
              </button>
              <button
                onClick={() => { toggleTheme(); setMobileNavOpen(false) }}
                className="text-sm opacity-70 hover:opacity-100 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[var(--card-border)] transition-colors"
                aria-label={theme === 'dark' ? t('aria.switchToLight') : t('aria.switchToDark')}
              >
                <span>{theme === 'dark' ? '☀️' : '🌙'}</span>
                <span>{theme === 'dark' ? t('nav.themeLight') : t('nav.themeDark')}</span>
              </button>
              <button
                onClick={() => { logout(); setMobileNavOpen(false) }}
                className="text-sm text-red-500 ml-auto"
              >
                {t('nav.logout')}
              </button>
            </div>
          </div>
        </div>
      )}

      <main id="main-content" className={`flex-1 flex flex-col p-4 max-w-6xl mx-auto w-full ${isChatRoute ? 'min-h-0' : 'main-pb-safe-bottom'}`}>
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 nav-bar safe-area-bottom" style={{ borderRadius: 0 }}>
        <div className="flex items-center justify-around py-2">
          {bottomNavLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={() => { setMobileNavOpen(false); setMoreOpen(false) }}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors ${isActive ? 'text-orange-500' : 'opacity-60'}`
              }
            >
              <img src={link.icon} alt="" className="w-8 h-8 object-contain" />
              <span className="truncate max-w-[4.5rem]">{link.label}</span>
            </NavLink>
          ))}
          {/* More button */}
          <div className="relative" ref={moreRef}>
            <button
              onClick={() => setMoreOpen(!moreOpen)}
              className={`flex flex-col items-center gap-0.5 px-2 py-1 text-xs transition-colors cursor-pointer ${moreOpen ? 'text-orange-500' : 'opacity-60'}`}
            >
              <span className="text-lg">{'\u2630'}</span>
              <span>{t('nav.more')}</span>
            </button>
            {moreOpen && (
              <div className="absolute bottom-full right-0 mb-2 w-48 rounded-xl shadow-xl z-50 border border-[var(--card-border)] bg-[var(--tooltip-bg)] py-2 max-h-[60vh] overflow-y-auto">
                {moreNavLinks.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    onClick={() => { setMoreOpen(false); setMobileNavOpen(false) }}
                    className={({ isActive }) =>
                      `block px-4 py-2.5 text-sm transition-colors flex items-center gap-2 ${isActive ? 'text-orange-500' : 'opacity-70 hover:opacity-100'}`
                    }
                  >
                    <img src={link.icon} alt="" className="w-7 h-7 object-contain" />
                    {link.label}
                  </NavLink>
                ))}
                {user?.is_staff && (
                  <NavLink
                    to="/admin"
                    onClick={() => { setMoreOpen(false); setMobileNavOpen(false) }}
                    className={({ isActive }) =>
                      `block px-4 py-2.5 text-sm transition-colors flex items-center gap-2 ${isActive ? 'text-orange-500' : 'opacity-70 hover:opacity-100'}`
                    }
                  >
                    <span>{'\u2699\uFE0F'}</span>
                    {t('nav.admin')}
                  </NavLink>
                )}
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Footer */}
      <footer className="text-center text-xs opacity-40 py-4 space-x-4">
        <Link to="/privacy" className="hover:opacity-70">{t('legal.privacy')}</Link>
        <Link to="/terms" className="hover:opacity-70">{t('legal.terms')}</Link>
        <span>&copy; {new Date().getFullYear()} HeartBox</span>
      </footer>

      {/* Idle Warning Modal */}
      {idleWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="popup-panel p-6 w-full max-w-sm text-center space-y-4" role="dialog" aria-modal="true">
            <h2 className="text-lg font-semibold">{t('idle.warningTitle')}</h2>
            <p className="opacity-70">{t('idle.warningDesc')}</p>
            <p className="text-3xl font-bold text-orange-500">{idleCountdown}s</p>
            <button onClick={dismissIdle} className="btn-primary">{t('idle.stayLoggedIn')}</button>
          </div>
        </div>
      )}

      {/* Onboarding Modal (lazy — only loaded for users who haven't seen it) */}
      {!onboardingDone && (
        <Suspense fallback={null}>
          <OnboardingModal onComplete={() => setOnboardingDone(true)} />
        </Suspense>
      )}
    </div>
  )
}
