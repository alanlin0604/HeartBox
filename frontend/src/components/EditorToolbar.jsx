import { useState, useEffect, useCallback } from 'react'
import { useLang } from '../context/LanguageContext'

export default function EditorToolbar({ editor, showVoice = false, isListening = false, onToggleVoice }) {
  const { t } = useLang()
  // Track toolbar state internally via editor transactions (avoids parent forceUpdate)
  const [, setTick] = useState(0)

  useEffect(() => {
    if (!editor) return
    const handler = () => setTick((n) => n + 1)
    editor.on('transaction', handler)
    return () => editor.off('transaction', handler)
  }, [editor])

  if (!editor) return null

  return (
    <div className="flex items-center gap-1 px-3 py-2 border-b border-[var(--card-border)]">
      <button type="button" onClick={() => editor.chain().focus().toggleBold().run()}
        className={`px-2 py-1 rounded text-xs font-bold transition-colors cursor-pointer ${editor.isActive('bold') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>{t('noteForm.bold')}</button>
      <button type="button" onClick={() => editor.chain().focus().toggleItalic().run()}
        className={`px-2 py-1 rounded text-xs italic transition-colors cursor-pointer ${editor.isActive('italic') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>{t('noteForm.italic')}</button>
      <button type="button" onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={`px-2 py-1 rounded text-xs transition-colors cursor-pointer ${editor.isActive('bulletList') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>{t('noteForm.list')}</button>
      <div className="w-px h-5 bg-[var(--card-border)] mx-1" />
      <button type="button" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()}
        className="px-2 py-1 rounded text-xs opacity-50 hover:opacity-100 disabled:opacity-20 cursor-pointer disabled:cursor-not-allowed">{t('noteForm.undo')}</button>
      <button type="button" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()}
        className="px-2 py-1 rounded text-xs opacity-50 hover:opacity-100 disabled:opacity-20 cursor-pointer disabled:cursor-not-allowed">{t('noteForm.redo')}</button>
      {showVoice && (
        <>
          <div className="w-px h-5 bg-[var(--card-border)] mx-1" />
          <button type="button" onClick={onToggleVoice}
            className={`p-1.5 rounded text-sm transition-colors ${isListening ? 'bg-red-500/30 text-red-400 animate-pulse' : 'opacity-50 hover:opacity-100'}`}
            title={t('noteForm.voiceInput')}>
            {isListening ? '\u{1F534}' : '\u{1F3A4}'}
          </button>
        </>
      )}
    </div>
  )
}
