import { memo } from 'react'

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export default memo(function HighlightText({ text, keyword }) {
  if (!keyword) return text
  const safe = escapeRegExp(keyword.trim())
  if (!safe) return text
  const regex = new RegExp(`(${safe})`, 'ig')
  const parts = String(text).split(regex)
  const matcher = new RegExp(`^${safe}$`, 'i')
  return (
    <>
      {parts.map((part, idx) => (
        matcher.test(part)
          ? <mark key={`${part}-${idx}`} className="rounded bg-yellow-300/40 px-0.5 text-inherit">{part}</mark>
          : <span key={`${part}-${idx}`}>{part}</span>
      ))}
    </>
  )
})
