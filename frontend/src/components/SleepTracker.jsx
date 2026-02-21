import { useState, useEffect } from 'react'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { getSleep, saveSleep } from '../api/sleep'

const QUALITY_OPTIONS = [
  { value: 1, labelKey: 'noteForm.sleepQuality1' },
  { value: 2, labelKey: 'noteForm.sleepQuality2' },
  { value: 3, labelKey: 'noteForm.sleepQuality3' },
  { value: 4, labelKey: 'noteForm.sleepQuality4' },
  { value: 5, labelKey: 'noteForm.sleepQuality5' },
]

export default function SleepTracker() {
  const { t } = useLang()
  const toast = useToast()
  const today = new Date().toISOString().split('T')[0]

  const [hours, setHours] = useState('')
  const [quality, setQuality] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSleep(today)
      .then((res) => {
        if (res.data.sleep_hours != null) {
          setHours(String(res.data.sleep_hours))
          setQuality(res.data.sleep_quality || 0)
          setSaved(true)
        }
      })
      .catch(() => {})
  }, [today])

  const handleSave = async () => {
    if (!hours || !quality) return
    setSaving(true)
    try {
      await saveSleep({ date: today, sleep_hours: parseFloat(hours), sleep_quality: quality })
      setSaved(true)
      toast?.success(t('sleep.saved'))
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="glass p-4 sm:p-5 space-y-3">
      <h2 className="text-base font-semibold">{t('sleep.title')}</h2>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <label className="block text-xs opacity-60 mb-1">{t('noteForm.sleepHours')}</label>
          <input
            type="number"
            value={hours}
            onChange={(e) => { setHours(e.target.value); setSaved(false) }}
            placeholder="7.5"
            min="0"
            max="24"
            step="0.5"
            className="glass-input w-full"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs opacity-60 mb-1">{t('noteForm.sleepQuality')}</label>
          <div className="flex gap-1">
            {QUALITY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => { setQuality(opt.value); setSaved(false) }}
                title={t(opt.labelKey)}
                className={`flex-1 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                  quality === opt.value
                    ? 'bg-purple-500/30 text-purple-400 border border-purple-500/40'
                    : 'border border-[var(--card-border)] opacity-60 hover:opacity-100'
                }`}
              >
                {opt.value}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-end">
          <button
            onClick={handleSave}
            disabled={!hours || !quality || saving || saved}
            className="btn-primary text-sm whitespace-nowrap"
          >
            {saving ? t('settings.saving') : saved ? t('sleep.recorded') : t('common.save')}
          </button>
        </div>
      </div>
    </div>
  )
}
