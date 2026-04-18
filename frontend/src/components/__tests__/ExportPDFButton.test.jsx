import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ExportPDFButton from '../ExportPDFButton'

// Mock context hooks
vi.mock('../../context/LanguageContext', () => ({
  useLang: () => ({
    t: (key) => {
      const translations = {
        'export.button': 'Export',
        'export.title': 'Export Notes',
        'export.format': 'Format',
        'export.from': 'From',
        'export.to': 'To',
        'export.download': 'Download PDF',
        'export.downloadPDF': 'Download PDF',
        'export.downloadCSV': 'Download CSV',
        'aria.exportNotes': 'Export notes',
      }
      return translations[key] || key
    },
    lang: 'en',
    setLang: vi.fn(),
  }),
}))

vi.mock('../../context/ToastContext', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}))

vi.mock('../../api/notes', () => ({
  exportNotesPDF: vi.fn(),
  exportNotesCSV: vi.fn(),
}))

describe('ExportPDFButton', () => {
  it('renders the export button with translated label', () => {
    render(<ExportPDFButton />)
    const button = screen.getByRole('button', { name: 'Export notes' })
    expect(button).toBeInTheDocument()
    expect(button).toHaveTextContent('Export')
  })

  it('expands the panel when the button is clicked', () => {
    render(<ExportPDFButton />)
    // Panel should not be visible initially
    expect(screen.queryByText('Export Notes')).not.toBeInTheDocument()

    // Click to expand
    fireEvent.click(screen.getByRole('button', { name: 'Export notes' }))

    // Panel should now be visible (component renders both desktop and mobile versions)
    expect(screen.getAllByText('Export Notes')).toHaveLength(2)
    expect(screen.getAllByText('Format')).toHaveLength(2)
  })

  it('toggles format between PDF and CSV and hides date fields for CSV', () => {
    render(<ExportPDFButton />)
    // Expand panel
    fireEvent.click(screen.getByRole('button', { name: 'Export notes' }))

    // Default format is PDF - date fields should be visible (2 instances: desktop + mobile)
    const formatSelects = screen.getAllByDisplayValue('PDF')
    expect(formatSelects).toHaveLength(2)
    expect(screen.getAllByText('From')).toHaveLength(2)
    expect(screen.getAllByText('To')).toHaveLength(2)

    // Switch to CSV (change both selects)
    formatSelects.forEach(select => fireEvent.change(select, { target: { value: 'csv' } }))

    // Date fields should be hidden for CSV format
    expect(screen.queryByText('From')).not.toBeInTheDocument()
    expect(screen.queryByText('To')).not.toBeInTheDocument()

    // Download button text should reflect CSV format (2 instances)
    expect(screen.getAllByText('Download CSV')).toHaveLength(2)
  })
})
