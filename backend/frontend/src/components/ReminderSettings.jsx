import { useEffect, useState } from 'react'
import { reminderAPI } from '../api/reminders'
import { useLang } from '../context/LanguageContext'

export default function ReminderSettings() {
  const { t } = useLang()
  const [settings, setSettings] = useState({ enabled: true, reminder_time: '20:00' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      setLoading(true)
      const data = await reminderAPI.getSettings()
      setSettings(data)
    } catch (err) {
      console.error('Failed to load reminder settings:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    try {
      setSaving(true)
      await reminderAPI.updateSettings(settings)
    } catch (err) {
      console.error('Failed to save reminder settings:', err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('reminder.title')}</h2>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-4">{t('reminder.title')}</h2>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">{t('reminder.enabled')}</p>
            <p className="text-sm text-slate-400">{t('reminder.enabledHint')}</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-purple-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
          </label>
        </div>

        {settings.enabled && (
          <div>
            <label className="block mb-2 font-medium">{t('reminder.time')}</label>
            <input
              type="time"
              value={settings.reminder_time}
              onChange={(e) => setSettings({ ...settings, reminder_time: e.target.value })}
              className="glass-input w-full"
            />
            <p className="text-xs text-slate-400 mt-1">{t('reminder.timeHint')}</p>
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary w-full"
        >
          {saving ? t('saving') : t('save')}
        </button>
      </div>
    </div>
  )
}
