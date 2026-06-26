// Renders LLM-generated feedback with proper visual hierarchy.
//
// Shape the model typically emits:
//
//   親愛的朋友，看到你最近工作上...  (intro paragraph)
//
//   面對工作壓力和沮喪的感覺，這裡有一些小建議...
//
//   1. 辨識自己的需求：試著問問自己，在如此大的壓力下...
//   2. 放鬆身心：嘗試做一些能讓你放鬆的活動...
//   3. 與他人談論你的感受：與人交談是抒發情緒...
//
//   如果你的工作壓力和情緒困擾持續存在...  (closing paragraph)
//
// Previous version rendered everything at opacity-80 with font-semibold,
// which made the numbered headings visually disappear. This rewrite gives
// each list item: bold accent-colored heading, visible row spacing, and
// the closing paragraph proper breathing room.

const NUMBERED_LINE_RE = /^(\d+)[.．、]\s*/  // 1. / 1． / 1、

function splitHeading(line) {
  // `1. 標題：內文` -> ['1. 標題：', '內文']
  // Trailing colon is part of the heading so the boundary reads naturally.
  const m = line.match(/^(\d+[.．、]\s*[^：:]{1,30}[：:])\s*(.*)$/)
  if (!m) return null
  return [m[1].trim(), m[2].trim()]
}

function ListItem({ line }) {
  const split = splitHeading(line)
  if (split) {
    const [heading, rest] = split
    // Heading rendered as a separate visually distinct chunk + body indented
    // below it so a long item doesn't read as one wall of text. The orange
    // accent matches the card border-l-4 on NoteDetailPage.
    return (
      <li className="pl-1">
        <div className="font-bold text-orange-500/90 mb-1">{heading}</div>
        {rest && <div className="opacity-90">{rest}</div>}
      </li>
    )
  }
  return <li className="pl-1 opacity-90">{line}</li>
}

function NumberedList({ items }) {
  // ``list-decimal`` reuses the model's "1./2./3." semantics for screen
  // readers AND removes the literal digits from the rendered text since we
  // already strip them via the heading regex. We add proper `space-y-3`
  // so each item visually separates from the next.
  return (
    <ol className="list-none my-2 pl-0 space-y-3">
      {items.map((line, idx) => <ListItem key={idx} line={line} />)}
    </ol>
  )
}

function Paragraph({ text }) {
  return (
    <p className="mb-3 last:mb-0 opacity-90 whitespace-pre-wrap leading-relaxed">
      {text}
    </p>
  )
}

export default function AIFeedbackText({ text, className = '' }) {
  if (!text) return null
  // Normalise CRLF and trim trailing whitespace once.
  const normalised = String(text).replace(/\r\n/g, '\n').trim()

  // Step 1: tokenise into blocks. We split on blank lines AND on the
  // boundary between numbered/non-numbered lines so the model output
  //
  //   intro paragraph
  //   1. item one
  //   2. item two
  //   closing paragraph
  //
  // separates into three blocks (intro / list / closing) even when the
  // model forgot to put blank lines between them.
  const rawLines = normalised.split('\n')
  const blocks = []         // { kind: 'p' | 'list', lines: [...] }
  let cur = null
  for (const rawLine of rawLines) {
    const line = rawLine.trim()
    if (!line) {
      if (cur) { blocks.push(cur); cur = null }
      continue
    }
    const isNumbered = NUMBERED_LINE_RE.test(line)
    const desiredKind = isNumbered ? 'list' : 'p'
    if (!cur || cur.kind !== desiredKind) {
      if (cur) blocks.push(cur)
      cur = { kind: desiredKind, lines: [] }
    }
    cur.lines.push(line)
  }
  if (cur) blocks.push(cur)

  return (
    <div className={`text-sm leading-relaxed ${className}`}>
      {blocks.map((block, idx) => {
        if (block.kind === 'list') {
          return <NumberedList key={idx} items={block.lines} />
        }
        return <Paragraph key={idx} text={block.lines.join('\n')} />
      })}
    </div>
  )
}
