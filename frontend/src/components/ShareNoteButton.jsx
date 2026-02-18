import { useEffect, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { shareNote } from '../api/notes'
import { getCounselors } from '../api/counselors'

export default function ShareNoteButton({ noteId }) {
  const { t } = useLang()
  const [open, setOpen] = useState(false)
  const [counselors, setCounselors] = useState([])
  const [selectedCounselor, setSelectedCounselor] = useState('')
  const [isAnonymous, setIsAnonymous] = useState(false)
  const [sharing, setSharing] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open && counselors.length === 0) {
      getCounselors()
        .then((res) => setCounselors(res.data.results || res.data))
        .catch(() => {})
    }
  }, [open])

  const handleShare = async () => {
    if (!selectedCounselor) return
    setSharing(true)
    setError('')
    try {
      // selectedCounselor holds the CounselorProfile pk from the counselor list.
      // The backend ShareNoteView accepts counselor_id (profile pk).
      await shareNote(noteId, selectedCounselor, isAnonymous)
      setSuccess(true)
    } catch (err) {
      setError(err.response?.data?.error || t('share.failed'))
    } finally {
      setSharing(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="btn-secondary text-xs"
      >
        {t('share.button')}
      </button>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="glass rounded-2xl p-6 max-w-sm w-full space-y-4" role="dialog" aria-modal="true" aria-labelledby="share-modal-title">
        <div className="flex justify-between items-center">
          <h3 id="share-modal-title" className="font-semibold">{t('share.title')}</h3>
          <button onClick={() => setOpen(false)} className="opacity-60 hover:opacity-100 cursor-pointer text-xl">
            &times;
          </button>
        </div>

        {success ? (
          <div className="text-center py-4 space-y-2">
            <p className="text-green-500 font-semibold">{t('share.success')}</p>
            <button onClick={() => { setOpen(false); setSuccess(false) }} className="btn-primary text-sm">
              {t('booking.close')}
            </button>
          </div>
        ) : (
          <>
            {error && <p className="text-red-500 text-sm">{error}</p>}

            <div>
              <label className="text-sm opacity-60 block mb-1">{t('share.selectCounselor')}</label>
              <select
                value={selectedCounselor}
                onChange={(e) => setSelectedCounselor(e.target.value)}
                className="glass-input"
              >
                <option value="">{t('share.chooseCounselor')}</option>
                {counselors.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.username} — {c.specialty}
                  </option>
                ))}
              </select>
            </div>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isAnonymous}
                onChange={(e) => setIsAnonymous(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">{t('share.anonymous')}</span>
            </label>

            <button
              onClick={handleShare}
              disabled={!selectedCounselor || sharing}
              className="btn-primary w-full"
            >
              {sharing ? t('share.sharing') : t('share.confirm')}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
