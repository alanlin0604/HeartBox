import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { useEffect, forwardRef, useImperativeHandle } from 'react'
import EditorToolbar from './EditorToolbar'

const RichTextEditor = forwardRef(function RichTextEditor({
  initialContent = '',
  placeholder = 'Write something...',
  onUpdate,
  showToolbar = true,
  showVoice = false,
  isListening = false,
  onToggleVoice,
  className = 'prose prose-invert max-w-none px-4 py-3 min-h-[140px] focus:outline-none [&_.tiptap]:outline-none [&_.tiptap]:min-h-[120px]',
}, ref) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder }),
    ],
    content: initialContent,
    onUpdate: ({ editor }) => {
      if (onUpdate) {
        onUpdate(editor.getHTML())
      }
    },
  })

  // Update content when initialContent changes
  useEffect(() => {
    if (editor && initialContent !== editor.getHTML()) {
      editor.commands.setContent(initialContent)
    }
  }, [initialContent, editor])

  // Expose editor instance to parent via ref
  useImperativeHandle(ref, () => ({
    getHTML: () => editor?.getHTML() || '',
    getText: () => editor?.getText() || '',
    setContent: (content) => editor?.commands.setContent(content),
    insertContent: (content) => editor?.commands.insertContent(content),
    focus: (position) => editor?.commands.focus(position),
    clear: () => editor?.commands.clearContent(),
    isEmpty: () => editor?.isEmpty ?? true,
    editor, // Expose full editor instance if needed
  }), [editor])

  if (!editor) {
    return (
      <div className={className}>
        <div className="animate-pulse opacity-50">Loading editor...</div>
      </div>
    )
  }

  return (
    <div>
      {showToolbar && (
        <EditorToolbar
          editor={editor}
          showVoice={showVoice}
          isListening={isListening}
          onToggleVoice={onToggleVoice}
        />
      )}
      <EditorContent editor={editor} className={className} />
    </div>
  )
})

export default RichTextEditor
