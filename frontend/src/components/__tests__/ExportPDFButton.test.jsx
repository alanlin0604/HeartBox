import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ExportPDFButton from '../ExportPDFButton'

// Mock context hooks
vi.mock('../../context/LanguageContext', () => ({
  useLang: () => ({
    t: (key) => key,
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
    expect(button).toHaveTextContent('export.button')
  })

  it('expands the panel when the button is clicked', () => {
    render(<ExportPDFButton />)
    // Panel should not be visible initially
    expect(screen.queryByText('export.title')).not.toBeInTheDocument()

    // Click to expand
    fireEvent.click(screen.getByRole('button', { name: 'Export notes' }))

    // Panel should now be visible
    expect(screen.getByText('export.title')).toBeInTheDocument()
    expect(screen.getByText('export.format')).toBeInTheDocument()
  })

  it('toggles format between PDF and CSV and hides date fields for CSV', () => {
    render(<ExportPDFButton />)
    // Expand panel
    fireEvent.click(screen.getByRole('button', { name: 'Export notes' }))

    // Default format is PDF - date fields should be visible
    const formatSelect = screen.getByDisplayValue('PDF')
    expect(formatSelect).toBeInTheDocument()
    expect(screen.getByText('export.from')).toBeInTheDocument()
    expect(screen.getByText('export.to')).toBeInTheDocument()

    // Switch to CSV
    fireEvent.change(formatSelect, { target: { value: 'csv' } })

    // Date fields should be hidden for CSV format
    expect(screen.queryByText('export.from')).not.toBeInTheDocument()
    expect(screen.queryByText('export.to')).not.toBeInTheDocument()

    // Download button text should reflect CSV format
    expect(screen.getByText('export.downloadCSV')).toBeInTheDocument()
  })
})
