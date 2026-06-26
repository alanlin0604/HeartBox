// Cross-references the user's personal_insights (historical mood patterns)
// with today's local weather to produce 2–4 personalised one-line tips
// (practical weather + insight-based nudges) above the journal write form.
//
// Weather: Open-Meteo current/daily, no API key. Location defaults to
// Taipei (HeartBox is TW-first and the Pages site has geolocation=()
// in Permissions-Policy, so we can't ask the browser).
//
// Renders null until weather resolves AND there's at least one tip — the
// section is meant to feel earned, not noisy.

import { useEffect, useState, useMemo } from 'react'
import { useLang } from '../context/LanguageContext'

const DEFAULT_LAT = 25.0478   // Taipei
const DEFAULT_LON = 121.5319

// WMO weather code → coarse bucket for our copy
function bucketFromCode(code) {
  if (code === 0 || code === 1) return 'clear'
  if (code === 2 || code === 3) return 'cloudy'
  if (code === 45 || code === 48) return 'fog'
  if (code >= 51 && code <= 67) return 'rain'
  if (code >= 71 && code <= 77) return 'snow'
  if (code >= 80 && code <= 82) return 'rain'
  if (code >= 85 && code <= 86) return 'snow'
  if (code >= 95 && code <= 99) return 'storm'
  return 'cloudy'
}

function todayPhase(day) {
  if (day <= 10) return 'early'
  if (day <= 20) return 'mid'
  return 'late'
}

function buildTips({ insights, weather, today, t }) {
  const tips = []
  if (!weather) return tips

  const bucket = weather.bucket
  const tempMax = weather.tempMax
  const tempMin = weather.tempMin

  // 1) Practical weather (max 1)
  if (bucket === 'storm') {
    tips.push({ tone: 'warn', text: t('dailySuggestion.tip.stormPractical') })
  } else if (bucket === 'rain') {
    tips.push({ tone: 'info', text: t('dailySuggestion.tip.rainPractical') })
  } else if (bucket === 'snow') {
    tips.push({ tone: 'warn', text: t('dailySuggestion.tip.snowPractical') })
  } else if (tempMax >= 32) {
    tips.push({ tone: 'warn', text: t('dailySuggestion.tip.hot', { temp: tempMax.toFixed(0) }) })
  } else if (tempMin <= 12) {
    tips.push({ tone: 'info', text: t('dailySuggestion.tip.cold', { temp: tempMin.toFixed(0) }) })
  }

  // 2) Personal-insight cross-references
  const day = today.getDate()
  const month = today.getMonth() + 1
  const dow = today.getDay()
  const isWeekend = dow === 0 || dow === 6
  const phase = todayPhase(day)
  const tempAvg = (tempMax + tempMin) / 2

  if (Array.isArray(insights)) {
    for (const ins of insights) {
      if (ins.key === 'month_phase' && ins.worst_phase === phase) {
        tips.push({ tone: 'support', text: t('dailySuggestion.tip.lowPhase') })
      }
      if (ins.key === 'weekday_weekend') {
        const todaySide = isWeekend ? 'weekend' : 'weekday'
        if (ins.better && ins.better !== todaySide) {
          tips.push({ tone: 'support', text: t('dailySuggestion.tip.lowDay') })
        }
      }
      if (ins.key === 'month_extremes' && ins.worst_month === month) {
        tips.push({ tone: 'support', text: t('dailySuggestion.tip.lowMonth') })
      }
      if (ins.key === 'weather_sun_rain' && bucket === 'rain' && ins.better === 'sunny') {
        tips.push({ tone: 'support', text: t('dailySuggestion.tip.rainMoodLow') })
      }
      if (ins.key === 'temperature_band') {
        if (ins.better === 'warm' && tempAvg < 20) {
          tips.push({ tone: 'support', text: t('dailySuggestion.tip.coldMoodLow') })
        } else if (ins.better === 'cold' && tempAvg >= 25) {
          tips.push({ tone: 'support', text: t('dailySuggestion.tip.warmMoodLow') })
        }
      }
    }
  }

  // Dedupe identical strings (rare but possible if templates collide) + cap
  const seen = new Set()
  return tips.filter((t) => {
    if (seen.has(t.text)) return false
    seen.add(t.text)
    return true
  }).slice(0, 4)
}

function toneClasses(tone) {
  if (tone === 'warn') return 'border-l-2 border-amber-500 bg-amber-500/5'
  if (tone === 'support') return 'border-l-2 border-orange-500 bg-orange-500/5'
  return 'border-l-2 border-sky-500/60 bg-sky-500/5'
}

export default function DailySuggestion({ insights }) {
  const { t, lang } = useLang()
  const [weather, setWeather] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${DEFAULT_LAT}&longitude=${DEFAULT_LON}&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1`
    fetch(url)
      .then((r) => r.ok ? r.json() : Promise.reject(new Error('http')))
      .then((data) => {
        if (cancelled) return
        const code = data?.daily?.weather_code?.[0] ?? data?.current?.weather_code ?? 0
        const tempMax = data?.daily?.temperature_2m_max?.[0]
        const tempMin = data?.daily?.temperature_2m_min?.[0]
        const tempNow = data?.current?.temperature_2m
        if (tempMax == null || tempMin == null) throw new Error('shape')
        setWeather({ code, bucket: bucketFromCode(code), tempMax, tempMin, tempNow })
      })
      .catch(() => { if (!cancelled) setFailed(true) })
    return () => { cancelled = true }
  }, [])

  const today = useMemo(() => new Date(), [])
  const tips = useMemo(
    () => buildTips({ insights, weather, today, t }),
    [insights, weather, today, t],
  )

  // Hide entirely if weather fetch failed AND no insight-only tips, or if
  // we have no tips at all. Avoids a half-empty card.
  if (failed && tips.length === 0) return null
  if (!weather && tips.length === 0) return null
  if (weather && tips.length === 0) return null

  const conditionLabel = weather ? t(`dailySuggestion.weather.${weather.bucket}`) : ''
  const tempDate = new Intl.DateTimeFormat(lang || 'zh-TW', { month: 'short', day: 'numeric' }).format(today)

  return (
    <div className="glass-card p-4 border-l-4 border-orange-500/50">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <h3 className="text-sm font-semibold text-orange-400 mb-0.5">
            {t('dailySuggestion.title')}
          </h3>
          {weather && (
            <p className="text-xs opacity-60">
              {tempDate}．{conditionLabel}．{Math.round(weather.tempMin)}° / {Math.round(weather.tempMax)}°C
              {weather.tempNow != null && (
                <> ．{t('dailySuggestion.now', { temp: Math.round(weather.tempNow) })}</>
              )}
            </p>
          )}
        </div>
      </div>
      <ul className="space-y-1.5">
        {tips.map((tip, i) => (
          <li key={i} className={`text-sm rounded-r px-3 py-1.5 ${toneClasses(tip.tone)}`}>
            {tip.text}
          </li>
        ))}
      </ul>
    </div>
  )
}
