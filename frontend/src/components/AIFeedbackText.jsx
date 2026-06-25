// Renders LLM-generated feedback with light structural formatting:
//   * Paragraphs separated by `\n\n` become <p> with `mb-3` spacing.
//   * Lines starting with `1.` / `2.` etc. become a numbered list with the
//     heading portion (text before the first ：/: colon) bolded.
//   * Other text renders verbatim with `whitespace-pre-wrap`.
// Defensive: empty / null input returns null. Plain text without any list
// shape falls through to a single <p>, so this is a drop-in replacement
// for `<p className="...">{ai_feedback}</p>`.

const NUMBERED_LINE_RE = /^(\d+)[.．]\s+/  // 1. or 1．
const NUMBERED_SPLIT_RE = /(?=^\d+[.．]\s+)/m

function splitHeading(line) {
  // Return [heading, rest] when the line is `1. 標題：內文` shape, else null.
  const m = line.match(/^(\d+[.．]\s+[^：:]+[：:])(.*)$/)
  if (!m) return null
  return [m[1].trim(), m[2].trim()]
}

function renderListItems(items) {
  return (
    <ol className="list-none space-y-2 my-1 pl-0">
      {items.map((line, idx) => {
        const split = splitHeading(line)
        if (split) {
          const [heading, rest] = split
          return (
            <li key={idx}>
              <span className="font-semibold">{heading}</span>
              {rest && <span> {rest}</span>}
            </li>
          )
        }
        return <li key={idx}>{line}</li>
      })}
    </ol>
  )
}

export default function AIFeedbackText({ text, className = '' }) {
  if (!text) return null
  // Normalise CRLF and trim trailing whitespace once.
  const normalised = String(text).replace(/\r\n/g, '\n').trim()

  const paragraphs = normalised.split(/\n\s*\n/)
  return (
    <div className={`text-sm leading-relaxed whitespace-pre-wrap opacity-80 ${className}`}>
      {paragraphs.map((para, pIdx) => {
        const lines = para.split('\n').map((l) => l.trim()).filter(Boolean)
        // If the paragraph is a contiguous block of numbered lines, render it
        // as a list. Otherwise render as a plain paragraph (whitespace-pre-wrap
        // already preserves embedded newlines).
        const allNumbered = lines.length >= 2 && lines.every((l) => NUMBERED_LINE_RE.test(l))
        if (allNumbered) {
          return <div key={pIdx} className="mb-3 last:mb-0">{renderListItems(lines)}</div>
        }
        // Sometimes the model emits the list on one line separated by '\n' but
        // mixed with a leading non-numbered sentence — split at first numbered.
        const firstNumIdx = lines.findIndex((l) => NUMBERED_LINE_RE.test(l))
        if (firstNumIdx > 0 && lines.slice(firstNumIdx).every((l) => NUMBERED_LINE_RE.test(l))) {
          return (
            <div key={pIdx} className="mb-3 last:mb-0">
              <p>{lines.slice(0, firstNumIdx).join('\n')}</p>
              {renderListItems(lines.slice(firstNumIdx))}
            </div>
          )
        }
        return (
          <p key={pIdx} className="mb-3 last:mb-0">
            {para}
          </p>
        )
      })}
    </div>
  )
}
