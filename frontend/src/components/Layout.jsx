import { useState, useRef, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import NotificationBell from './NotificationBell'

const LANG_OPTIONS = [
  { code: 'zh-TW', label: 'ZH' },
  { code: 'en', label: 'EN' },
  { code: 'ja', label: 'JA' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { lang, setLang, t } = useLang()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const menuRef = useRef(null)

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
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

  const navLinks = [
    { to: '/', label: t('nav.journal'), end: true },
    { to: '/dashboard', label: t('nav.dashboard') },
    { to: '/counselors', label: t('nav.counselors') },
    { to: '/ai-chat', label: t('nav.aiChat') },
    { to: '/achievements', label: t('nav.achievements') },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Offline banner */}
      {isOffline && (
        <div className="bg-yellow-500/90 text-black text-center text-sm py-1.5 px-4 font-medium">
          {t('common.offline')}
        </div>
      )}

      <nav className="glass sticky top-0 z-50 mx-4 mt-4 px-6 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          {t('app.displayName')}
        </h1>

        {/* Mobile: notification bell + hamburger (always visible) */}
        <div className="md:hidden flex items-center gap-3">
          <NotificationBell />
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
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
        <div className="hidden md:flex items-center gap-4 text-base">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `font-medium transition-colors ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
              }
            >
              {link.label}
            </NavLink>
          ))}
          {user?.is_staff && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `font-medium transition-colors ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
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
                <img src={user.avatar} alt={user.username} loading="lazy" className="w-7 h-7 rounded-full object-cover border border-white/20" />
              ) : (
                <span className="w-7 h-7 rounded-full bg-purple-500/25 text-xs flex items-center justify-center">
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
                  className="w-full text-left px-4 py-2.5 text-sm hover:bg-purple-500/10 transition-colors cursor-pointer flex items-center gap-2"
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
                  className="w-full text-left px-4 py-2.5 text-sm hover:bg-purple-500/10 transition-colors cursor-pointer flex items-center gap-2"
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
                            ? 'bg-purple-500/30 text-purple-500 font-bold'
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
        <div className="md:hidden glass mx-4 mt-2 p-4 space-y-3 z-40">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              onClick={() => setMobileNavOpen(false)}
              className={({ isActive }) =>
                `block font-medium transition-colors py-1 ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
              }
            >
              {link.label}
            </NavLink>
          ))}
          {user?.is_staff && (
            <NavLink
              to="/admin"
              onClick={() => setMobileNavOpen(false)}
              className={({ isActive }) =>
                `block font-medium transition-colors py-1 ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
              }
            >
              {t('nav.admin')}
            </NavLink>
          )}
          <div className="border-t border-[var(--card-border)] pt-3 flex flex-wrap items-center gap-3">
            <button
              onClick={() => { navigate('/settings'); setMobileNavOpen(false) }}
              className="text-sm opacity-60 hover:opacity-100"
            >
              {t('settings.title')}
            </button>
            <button
              onClick={() => { toggleTheme(); setMobileNavOpen(false) }}
              className="text-sm opacity-70 hover:opacity-100 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[var(--card-border)] transition-colors"
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
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
      )}

      <main className="flex-1 flex flex-col p-4 max-w-6xl mx-auto w-full">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="text-center text-xs opacity-40 py-4 space-x-4">
        <Link to="/privacy" className="hover:opacity-70">{t('legal.privacy')}</Link>
        <Link to="/terms" className="hover:opacity-70">{t('legal.terms')}</Link>
        <span>&copy; {new Date().getFullYear()} HeartBox</span>
      </footer>
    </div>
  )
}
