import { useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { getAvailableSlots, createBooking } from '../api/schedule'
import { useToast } from '../context/ToastContext'

function formatPrice(amount, currency = 'TWD') {
  const num = Number(amount)
  if (isNaN(num)) return ''
  const symbols = { TWD: 'NT$', USD: '$', JPY: '\u00A5' }
  const prefix = symbols[currency] || currency + ' '
  return `${prefix} ${num.toLocaleString()}`
}

export default function BookingPanel({ counselorId, counselorName, hourlyRate, currency, onClose }) {
  const { t } = useLang()
  const toast = useToast()
  const [date, setDate] = useState('')
  const [slots, setSlots] = useState([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [booking, setBooking] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleDateChange = async (e) => {
    const val = e.target.value
    setDate(val)
    if (!val) return

    // Validate selected date is not in the past
    const today = new Date().toISOString().split('T')[0]
    if (val < today) {
      toast?.error(t('booking.pastDate'))
      setDate('')
      setSlots([])
      return
    }

    setLoadingSlots(true)
    try {
      const res = await getAvailableSlots(counselorId, val)
      setSlots(res.data)
    } catch (err) {
      console.error('Failed to load slots', err)
      toast?.error(t('common.operationFailed'))
      setSlots([])
    } finally {
      setLoadingSlots(false)
    }
  }

  const handleBook = async (slot) => {
    setBooking(true)
    try {
      await createBooking({
        counselor_id: counselorId,
        date,
        start_time: slot.start_time,
        end_time: slot.end_time,
      })
      setSuccess(true)
      toast?.success(t('booking.success'))
    } catch (err) {
      toast?.error(err.response?.data?.error || t('booking.failed'))
    } finally {
      setBooking(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="glass rounded-2xl p-6 max-w-md w-full space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">
            {t('booking.title')} — {counselorName}
          </h3>
          <button onClick={onClose} className="opacity-60 hover:opacity-100 cursor-pointer text-xl">
            &times;
          </button>
        </div>

        {success ? (
          <div className="text-center py-6 space-y-2">
            <p className="text-green-500 font-semibold text-lg">{t('booking.success')}</p>
            <p className="opacity-60 text-sm">{t('booking.successMsg')}</p>
            <button onClick={onClose} className="btn-primary text-sm mt-4">
              {t('booking.close')}
            </button>
          </div>
        ) : (
          <>
            {hourlyRate && (
              <div className="glass-card p-3 text-center">
                <p className="text-sm opacity-60">{t('pricing.sessionFee')}</p>
                <p className="text-lg font-bold text-purple-500">
                  {formatPrice(hourlyRate, currency)} / {t('pricing.perHour')}
                </p>
              </div>
            )}
            <div>
              <label className="text-sm opacity-60 block mb-1">{t('booking.selectDate')}</label>
              <input
                type="date"
                value={date}
                onChange={handleDateChange}
                min={new Date().toISOString().split('T')[0]}
                className="glass-input"
              />
            </div>

            {date && (
              <div>
                <p className="text-sm font-medium mb-2">{t('booking.availableSlots')}</p>
                {loadingSlots ? (
                  <p className="text-sm opacity-60">{t('common.loading')}</p>
                ) : slots.length === 0 ? (
                  <p className="text-sm opacity-60">{t('booking.noSlots')}</p>
                ) : (
                  <div className="grid gap-2 grid-cols-2">
                    {slots.map((slot) => (
                      <button
                        key={slot.id}
                        onClick={() => handleBook(slot)}
                        disabled={booking}
                        className="glass-card p-3 text-center cursor-pointer hover:border-purple-500/30 transition-all"
                      >
                        <span className="text-sm font-medium">
                          {slot.start_time?.slice(0, 5)} - {slot.end_time?.slice(0, 5)}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
