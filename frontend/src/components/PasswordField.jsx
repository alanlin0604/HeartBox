import { useMemo, useState } from 'react'
import { evaluatePasswordStrength } from '../utils/passwordStrength'
import { useLang } from '../context/LanguageContext'

export default function PasswordField({
  id,
  value,
  onChange,
  placeholder,
  label,
  required = false,
  minLength,
  showStrength = false,
  autoComplete,
  className = 'glass-input',
}) {
  const { t } = useLang()
  const [visible, setVisible] = useState(false)
  const strength = useMemo(() => evaluatePasswordStrength(value || ''), [value])

  const barClass = strength.level === 'strong'
    ? 'bg-emerald-500'
    : strength.level === 'medium'
      ? 'bg-yellow-500'
      : 'bg-red-500'

  return (
    <div className="space-y-2">
      {label && <label htmlFor={id} className="sr-only">{label}</label>}
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          aria-label={label || placeholder}
          className={`${className} pr-12`}
          required={required}
          minLength={minLength}
          autoComplete={autoComplete}
        />
        <button
          type="button"
          onClick={() => setVisible((prev) => !prev)}
          className="absolute inset-y-0 right-3 text-sm opacity-60 hover:opacity-100"
          title={visible ? t('password.hide') : t('password.show')}
        >
          {visible ? t('password.hide') : t('password.show')}
        </button>
      </div>
      {showStrength && value && (
        <div className="space-y-1">
          <div className="h-1.5 rounded-full bg-white/10">
            <div className={`h-full rounded-full transition-all ${barClass}`} style={{ width: `${strength.value}%` }} />
          </div>
          <p className="text-xs opacity-70">
            {strength.level === 'strong'
              ? t('password.strong')
              : strength.level === 'medium'
                ? t('password.medium')
                : t('password.weak')}
          </p>
        </div>
      )}
    </div>
  )
}
