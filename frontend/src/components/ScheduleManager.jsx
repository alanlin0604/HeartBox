import { useEffect, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { getMySchedule, createTimeSlot, deleteTimeSlot } from '../api/schedule'

const DAY_KEYS = [
  'schedule.mon', 'schedule.tue', 'schedule.wed', 'schedule.thu',
  'schedule.fri', 'schedule.sat', 'schedule.sun',
]

export default function ScheduleManager() {
  const { t } = useLang()
  const [slots, setSlots] = useState([])
  const [loading, setLoading] = useState(true)
  const [dayOfWeek, setDayOfWeek] = useState(0)
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('10:00')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadSlots()
  }, [])

  const loadSlots = async () => {
    try {
      const res = await getMySchedule()
      setSlots(res.data)
    } catch (err) {
      console.error('Failed to load schedule', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await createTimeSlot({
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
      })
      setSlots((prev) => [...prev, res.data])
    } catch (err) {
      console.error('Failed to add slot', err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteTimeSlot(id)
      setSlots((prev) => prev.filter((s) => s.id !== id))
    } catch (err) {
      console.error('Failed to delete slot', err)
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{t('schedule.manageTitle')}</h3>

      {/* Add slot form */}
      <form onSubmit={handleAdd} className="glass p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs opacity-60 block mb-1">{t('schedule.dayOfWeek')}</label>
          <select
            value={dayOfWeek}
            onChange={(e) => setDayOfWeek(Number(e.target.value))}
            className="glass-input w-auto"
          >
            {DAY_KEYS.map((key, i) => (
              <option key={i} value={i}>{t(key)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs opacity-60 block mb-1">{t('schedule.startTime')}</label>
          <input
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            className="glass-input w-auto"
          />
        </div>
        <div>
          <label className="text-xs opacity-60 block mb-1">{t('schedule.endTime')}</label>
          <input
            type="time"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
            className="glass-input w-auto"
          />
        </div>
        <button type="submit" disabled={saving} className="btn-primary text-sm">
          {saving ? t('schedule.adding') : t('schedule.addSlot')}
        </button>
      </form>

      {/* Slot list */}
      {loading ? (
        <p className="opacity-60 text-sm">{t('common.loading')}</p>
      ) : slots.length === 0 ? (
        <p className="opacity-60 text-sm">{t('schedule.noSlots')}</p>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {slots.map((slot) => (
            <div key={slot.id} className="glass-card p-3 flex items-center justify-between">
              <div>
                <span className="font-medium text-sm">{t(DAY_KEYS[slot.day_of_week])}</span>
                <span className="text-sm opacity-60 ml-2">
                  {slot.start_time?.slice(0, 5)} - {slot.end_time?.slice(0, 5)}
                </span>
              </div>
              <button
                onClick={() => handleDelete(slot.id)}
                className="text-red-500 text-xs hover:text-red-400 cursor-pointer"
              >
                {t('schedule.delete')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
