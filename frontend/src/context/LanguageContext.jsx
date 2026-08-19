import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import zhTW from '../locales/zh-TW.json'
import en from '../locales/en.json'
import ja from '../locales/ja.json'
import { updateProfile } from '../api/auth'
import { getAccessToken } from '../utils/tokenStorage'

const translations = { 'zh-TW': zhTW, en, ja }

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setRawLang] = useState(() => {
    return localStorage.getItem('language') || 'zh-TW'
  })

  useEffect(() => {
    localStorage.setItem('language', lang)
    document.documentElement.lang = lang
  }, [lang])

  // Persist the choice on the account as well as in this browser. localStorage
  // alone is per-browser, not per-account: signing into an English account on a
  // machine that had ever used the app left the UI in Chinese, and the daily
  // writing prompt followed suit because Accept-Language is read from here.
  // Best-effort — a failed PATCH must not block the UI from switching.
  const setLang = useCallback((next) => {
    setRawLang(next)
    if (getAccessToken()) {
      updateProfile({ language: next }).catch(() => { /* keep the local switch */ })
    }
  }, [])

  // Adopt the language stored on the account, without writing it back. Used by
  // AuthContext when a profile loads; going through setLang there would PATCH
  // the value we just read.
  const adoptLang = useCallback((next) => {
    if (next && translations[next]) setRawLang(next)
  }, [])

  const t = useCallback(
    (key, vars) => {
      let text =
        translations[lang]?.[key] ||
        translations.en?.[key] ||
        translations['zh-TW']?.[key] ||
        key
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          text = text.replaceAll(`{${k}}`, v)
        })
      }
      return text
    },
    [lang],
  )

  const value = useMemo(
    () => ({ lang, setLang, adoptLang, t }),
    [lang, setLang, adoptLang, t],
  )

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useLang = () => useContext(LanguageContext)
