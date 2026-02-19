import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { getWellnessSessions, createWellnessSession } from '../api/breathe'
import { getCourses } from '../api/wellness'

const BREATHING_EXERCISES = [
  { id: '478', nameKey: 'breathe.478', steps: [
    { phase: 'inhale', duration: 4 },
    { phase: 'hold', duration: 7 },
    { phase: 'exhale', duration: 8 },
  ]},
  { id: 'box', nameKey: 'breathe.box', steps: [
    { phase: 'inhale', duration: 4 },
    { phase: 'hold', duration: 4 },
    { phase: 'exhale', duration: 4 },
    { phase: 'hold', duration: 4 },
  ]},
  { id: 'deep', nameKey: 'breathe.deep', steps: [
    { phase: 'inhale', duration: 4 },
    { phase: 'hold', duration: 2 },
    { phase: 'exhale', duration: 6 },
  ]},
]

const MEDITATION_DURATIONS = [1, 3, 5, 10, 15]

export default function BreathingPage() {
  const { t } = useLang()
  const navigate = useNavigate()
  const [tab, setTab] = useState('breathing')
  const [sessions, setSessions] = useState([])
  const [courseId, setCourseId] = useState(null)

  // Breathing state
  const [selectedExercise, setSelectedExercise] = useState(null)
  const [breathingActive, setBreathingActive] = useState(false)
  const [currentPhase, setCurrentPhase] = useState('')
  const [phaseTime, setPhaseTime] = useState(0)
  const [totalElapsed, setTotalElapsed] = useState(0)
  const [breathScale, setBreathScale] = useState(1)
  const [breathComplete, setBreathComplete] = useState(false)
  const breathIntervalRef = useRef(null)
  const breathStepRef = useRef(0)
  const breathPhaseCounterRef = useRef(0)
  const breathCyclesRef = useRef(0)
  const BREATH_CYCLES = 4

  // Meditation state
  const [medDuration, setMedDuration] = useState(5)
  const [medActive, setMedActive] = useState(false)
  const [medElapsed, setMedElapsed] = useState(0)
  const [medComplete, setMedComplete] = useState(false)
  const [ambientOn, setAmbientOn] = useState(false)
  const medIntervalRef = useRef(null)
  const audioCtxRef = useRef(null)
  const noiseNodeRef = useRef(null)
  const gainNodeRef = useRef(null)

  useEffect(() => { document.title = `${t('breathe.title')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    getWellnessSessions()
      .then(res => setSessions(res.data?.results || res.data || []))
      .catch(() => {})
    getCourses()
      .then(res => {
        const courses = res.data?.results || res.data || []
        const found = courses.find(c => c.title_en === 'Breathing & Meditation')
        if (found) setCourseId(found.id)
      })
      .catch(() => {})
  }, [])

  // Cleanup intervals and audio on unmount
  useEffect(() => {
    return () => {
      if (breathIntervalRef.current) clearInterval(breathIntervalRef.current)
      if (medIntervalRef.current) clearInterval(medIntervalRef.current)
      stopAmbient()
    }
  }, [])

  // --- Breathing logic ---
  const startBreathing = (exercise) => {
    setSelectedExercise(exercise)
    setBreathingActive(true)
    setBreathComplete(false)
    setTotalElapsed(0)
    breathStepRef.current = 0
    breathPhaseCounterRef.current = 0
    breathCyclesRef.current = 0

    const step = exercise.steps[0]
    setCurrentPhase(step.phase)
    setPhaseTime(step.duration)
    setBreathScale(step.phase === 'inhale' ? 1.6 : step.phase === 'exhale' ? 1.0 : 1.6)

    breathIntervalRef.current = setInterval(() => {
      setTotalElapsed(prev => prev + 1)
      setPhaseTime(prev => {
        if (prev <= 1) {
          // Move to next step
          breathPhaseCounterRef.current++
          const ex = exercise
          let nextIdx = (breathStepRef.current + 1) % ex.steps.length
          if (nextIdx === 0) {
            breathCyclesRef.current++
            if (breathCyclesRef.current >= BREATH_CYCLES) {
              clearInterval(breathIntervalRef.current)
              setBreathingActive(false)
              setBreathComplete(true)
              setCurrentPhase('')
              return 0
            }
          }
          breathStepRef.current = nextIdx
          const nextStep = ex.steps[nextIdx]
          setCurrentPhase(nextStep.phase)
          setBreathScale(nextStep.phase === 'inhale' ? 1.6 : nextStep.phase === 'exhale' ? 1.0 : (breathStepRef.current > 0 ? 1.6 : 1.0))
          return nextStep.duration
        }
        return prev - 1
      })
    }, 1000)
  }

  const stopBreathing = () => {
    if (breathIntervalRef.current) clearInterval(breathIntervalRef.current)
    setBreathingActive(false)
    setCurrentPhase('')
    setBreathScale(1)
  }

  const saveBreathingSession = async () => {
    if (!selectedExercise) return
    try {
      await createWellnessSession({
        session_type: 'breathing',
        exercise_name: selectedExercise.id,
        duration_seconds: totalElapsed,
      })
      const res = await getWellnessSessions()
      setSessions(res.data?.results || res.data || [])
      setBreathComplete(false)
      setSelectedExercise(null)
    } catch {}
  }

  // --- Meditation logic ---
  const startMeditation = () => {
    setMedActive(true)
    setMedComplete(false)
    setMedElapsed(0)
    const totalSec = medDuration * 60
    medIntervalRef.current = setInterval(() => {
      setMedElapsed(prev => {
        if (prev + 1 >= totalSec) {
          clearInterval(medIntervalRef.current)
          setMedActive(false)
          setMedComplete(true)
          return totalSec
        }
        return prev + 1
      })
    }, 1000)
  }

  const stopMeditation = () => {
    if (medIntervalRef.current) clearInterval(medIntervalRef.current)
    setMedActive(false)
  }

  const saveMeditationSession = async () => {
    try {
      await createWellnessSession({
        session_type: 'meditation',
        exercise_name: `${medDuration}min`,
        duration_seconds: medElapsed,
      })
      const res = await getWellnessSessions()
      setSessions(res.data?.results || res.data || [])
      setMedComplete(false)
    } catch {}
  }

  // --- Ambient sound ---
  const startAmbient = useCallback(() => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const bufferSize = 2 * ctx.sampleRate
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate)
      const data = buffer.getChannelData(0)
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1
      }
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.loop = true
      // Low-pass filter for softer sound
      const filter = ctx.createBiquadFilter()
      filter.type = 'lowpass'
      filter.frequency.value = 400
      const gain = ctx.createGain()
      gain.gain.value = 0.15
      source.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)
      source.start()
      audioCtxRef.current = ctx
      noiseNodeRef.current = source
      gainNodeRef.current = gain
      setAmbientOn(true)
    } catch {}
  }, [])

  const stopAmbient = useCallback(() => {
    try {
      noiseNodeRef.current?.stop()
      audioCtxRef.current?.close()
    } catch {}
    audioCtxRef.current = null
    noiseNodeRef.current = null
    setAmbientOn(false)
  }, [])

  const playChime = useCallback(() => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const now = ctx.currentTime

      // Fundamental 528Hz sine wave
      const osc1 = ctx.createOscillator()
      osc1.type = 'sine'
      osc1.frequency.value = 528
      const gain1 = ctx.createGain()
      gain1.gain.setValueAtTime(0.3, now)
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 3)
      osc1.connect(gain1)
      gain1.connect(ctx.destination)

      // Harmonic 1056Hz
      const osc2 = ctx.createOscillator()
      osc2.type = 'sine'
      osc2.frequency.value = 1056
      const gain2 = ctx.createGain()
      gain2.gain.setValueAtTime(0.15, now)
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 3)
      osc2.connect(gain2)
      gain2.connect(ctx.destination)

      osc1.start(now)
      osc2.start(now)
      osc1.stop(now + 3)
      osc2.stop(now + 3)

      setTimeout(() => ctx.close(), 3500)
    } catch {}
  }, [])

  // Play chime when breathing or meditation completes
  useEffect(() => {
    if (breathComplete || medComplete) playChime()
  }, [breathComplete, medComplete, playChime])

  const toggleAmbient = () => {
    if (ambientOn) stopAmbient()
    else startAmbient()
  }

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }

  const phaseLabel = currentPhase ? t(`breathe.phase.${currentPhase}`) : ''
  const totalMedSec = medDuration * 60
  const medProgress = totalMedSec > 0 ? medElapsed / totalMedSec : 0
  const circumference = 2 * Math.PI * 90

  return (
    <div className="space-y-6 mt-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold">{t('breathe.title')}</h1>

      {/* Learn More Banner */}
      {courseId && (
        <button
          onClick={() => navigate(`/learn/courses/${courseId}`)}
          className="glass p-4 w-full text-left flex items-center gap-3 hover:bg-purple-500/5 transition-colors cursor-pointer"
        >
          <span className="text-2xl">📚</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm opacity-80">{t('breathe.learnMore')}</p>
            <p className="text-sm font-semibold text-purple-400">{t('breathe.learnMoreLink')}</p>
          </div>
        </button>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setTab('breathing')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'breathing' ? 'bg-purple-500/30 text-purple-400' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('breathe.breathingTab')}
        </button>
        <button
          onClick={() => setTab('meditation')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'meditation' ? 'bg-purple-500/30 text-purple-400' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('breathe.meditationTab')}
        </button>
      </div>

      {tab === 'breathing' && (
        <div className="space-y-6">
          {/* Exercise selection or active exercise */}
          {!breathingActive && !breathComplete && (
            <div className="grid gap-3">
              {BREATHING_EXERCISES.map(ex => (
                <button
                  key={ex.id}
                  onClick={() => startBreathing(ex)}
                  className="glass p-4 text-left hover:bg-purple-500/5 transition-colors cursor-pointer"
                >
                  <h3 className="font-semibold">{t(ex.nameKey)}</h3>
                  <p className="text-xs text-purple-400 mt-0.5">{t(`breathe.desc.${ex.id}`)}</p>
                  <p className="text-sm opacity-60 mt-1">
                    {ex.steps.map(s => `${t(`breathe.phase.${s.phase}`)} ${s.duration}s`).join(' → ')}
                  </p>
                </button>
              ))}
            </div>
          )}

          {/* Active breathing animation */}
          {breathingActive && (
            <div className="glass p-8 flex flex-col items-center gap-6">
              <div className="relative w-48 h-48 flex items-center justify-center">
                <div
                  className="w-32 h-32 rounded-full bg-gradient-to-br from-purple-500/40 to-blue-500/40 flex items-center justify-center"
                  style={{
                    transform: `scale(${breathScale})`,
                    transition: `transform ${currentPhase === 'hold' ? '0.3s' : (currentPhase === 'inhale' ? '1s' : '1.5s')} ease-in-out`,
                  }}
                >
                  <div className="text-center">
                    <div className="text-lg font-bold">{phaseLabel}</div>
                    <div className="text-3xl font-mono">{phaseTime}</div>
                  </div>
                </div>
              </div>
              <p className="text-sm opacity-60">{t('breathe.elapsed')}: {formatTime(totalElapsed)}</p>
              <button
                onClick={stopBreathing}
                className="px-6 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors text-sm"
              >
                {t('breathe.stop')}
              </button>
            </div>
          )}

          {/* Completion */}
          {breathComplete && (
            <div className="glass p-6 text-center space-y-4">
              <div className="text-4xl">🎉</div>
              <h3 className="text-lg font-semibold">{t('breathe.completed')}</h3>
              <p className="text-sm opacity-60">{t('breathe.duration')}: {formatTime(totalElapsed)}</p>
              <button onClick={saveBreathingSession} className="btn-primary">
                {t('breathe.saveSession')}
              </button>
            </div>
          )}
        </div>
      )}

      {tab === 'meditation' && (
        <div className="space-y-6">
          {!medActive && !medComplete && (
            <div className="glass p-6 space-y-6">
              <h3 className="font-semibold">{t('breathe.selectDuration')}</h3>
              <div className="flex flex-wrap gap-3 justify-center">
                {MEDITATION_DURATIONS.map(d => (
                  <button
                    key={d}
                    onClick={() => setMedDuration(d)}
                    className={`w-16 h-16 rounded-full text-lg font-semibold transition-all ${
                      medDuration === d
                        ? 'bg-purple-500/30 text-purple-400 border-2 border-purple-500/40'
                        : 'border-2 border-[var(--card-border)] opacity-60 hover:opacity-100'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
              <p className="text-center text-sm opacity-60">{t('breathe.minutes')}</p>

              {/* Ambient sound toggle */}
              <div className="flex items-center justify-center gap-3">
                <span className="text-sm opacity-60">{t('breathe.ambientSound')}</span>
                <button
                  onClick={toggleAmbient}
                  className={`w-12 h-6 rounded-full transition-colors relative ${
                    ambientOn ? 'bg-purple-500' : 'bg-[var(--card-border)]'
                  }`}
                >
                  <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                    ambientOn ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>

              <button onClick={startMeditation} className="btn-primary w-full">
                {t('breathe.startMeditation')}
              </button>
            </div>
          )}

          {/* Active meditation */}
          {medActive && (
            <div className="glass p-8 flex flex-col items-center gap-6">
              <div className="relative w-52 h-52 flex items-center justify-center">
                <svg className="w-52 h-52 -rotate-90" viewBox="0 0 200 200">
                  <circle cx="100" cy="100" r="90" fill="none" stroke="var(--card-border)" strokeWidth="6" />
                  <circle
                    cx="100" cy="100" r="90" fill="none"
                    stroke="#a78bfa" strokeWidth="6" strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference * (1 - medProgress)}
                    style={{ transition: 'stroke-dashoffset 1s linear' }}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-3xl font-mono">{formatTime(medElapsed)}</span>
                </div>
              </div>
              <button
                onClick={stopMeditation}
                className="px-6 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors text-sm"
              >
                {t('breathe.stop')}
              </button>
            </div>
          )}

          {/* Meditation complete */}
          {medComplete && (
            <div className="glass p-6 text-center space-y-4">
              <div className="text-4xl">🧘</div>
              <h3 className="text-lg font-semibold">{t('breathe.meditationComplete')}</h3>
              <p className="text-sm opacity-60">{t('breathe.duration')}: {formatTime(medElapsed)}</p>
              <button onClick={saveMeditationSession} className="btn-primary">
                {t('breathe.saveSession')}
              </button>
            </div>
          )}
        </div>
      )}

      {/* History */}
      {sessions.length > 0 && (
        <div className="glass p-4 space-y-3">
          <h3 className="font-semibold text-sm opacity-60">{t('breathe.history')}</h3>
          <div className="space-y-2">
            {sessions.slice(0, 10).map(s => (
              <div key={s.id} className="flex items-center justify-between text-sm py-1.5 border-b border-[var(--card-border)] last:border-0">
                <div className="flex items-center gap-2">
                  <span>{s.session_type === 'breathing' ? '🌬️' : '🧘'}</span>
                  <span>{s.session_type === 'breathing' ? t(`breathe.exercise.${s.exercise_name}`) : `${s.exercise_name} ${t('breathe.meditation')}`}</span>
                </div>
                <div className="flex items-center gap-3 opacity-60">
                  <span>{formatTime(s.duration_seconds)}</span>
                  <span>{new Date(s.completed_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
