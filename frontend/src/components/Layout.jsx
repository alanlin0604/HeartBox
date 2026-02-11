import { useState, useRef, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
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

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="glass sticky top-0 z-50 mx-4 mt-4 px-6 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          HeartBox-心事盒
        </h1>
        <div className="flex items-center gap-4 text-base">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `font-medium transition-colors ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
            }
          >
            {t('nav.journal')}
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `font-medium transition-colors ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
            }
          >
            {t('nav.dashboard')}
          </NavLink>
          <NavLink
            to="/counselors"
            className={({ isActive }) =>
              `font-medium transition-colors ${isActive ? 'text-purple-500' : 'opacity-60 hover:opacity-100'}`
            }
          >
            {t('nav.counselors')}
          </NavLink>
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
                <img src={user.avatar} alt={user.username} className="w-7 h-7 rounded-full object-cover border border-white/20" />
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
      <main className="flex-1 p-4 max-w-6xl mx-auto w-full">
        <Outlet />
      </main>
    </div>
  )
}
