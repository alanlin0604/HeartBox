import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SearchFilterPanel from '../SearchFilterPanel'

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

describe('SearchFilterPanel', () => {
  it('renders the search input and submit button', () => {
    const onFilterChange = vi.fn()
    render(<SearchFilterPanel filters={{}} onFilterChange={onFilterChange} />)

    expect(screen.getByPlaceholderText('search.placeholder')).toBeInTheDocument()
    expect(screen.getByText('search.search')).toBeInTheDocument()
  })

  it('calls onFilterChange with search term on form submit', () => {
    const onFilterChange = vi.fn()
    render(<SearchFilterPanel filters={{}} onFilterChange={onFilterChange} />)

    const input = screen.getByPlaceholderText('search.placeholder')
    fireEvent.change(input, { target: { value: 'happy' } })
    fireEvent.submit(input.closest('form'))

    expect(onFilterChange).toHaveBeenCalledWith({ search: 'happy' })
  })

  it('expands filter panel when the toggle button is clicked', () => {
    const onFilterChange = vi.fn()
    render(<SearchFilterPanel filters={{}} onFilterChange={onFilterChange} />)

    // Filter fields should not be visible initially
    expect(screen.queryByText('search.tag')).not.toBeInTheDocument()

    // Click the expand button
    const expandButton = screen.getByRole('button', { name: 'Expand filters' })
    fireEvent.click(expandButton)

    // Filter fields should now be visible
    expect(screen.getByText('search.tag')).toBeInTheDocument()
    expect(screen.getByText('search.sentimentRange')).toBeInTheDocument()
    expect(screen.getByText('search.stressRange')).toBeInTheDocument()
    expect(screen.getByText('search.dateRange')).toBeInTheDocument()

    // Aria attributes should update
    expect(expandButton).toHaveAttribute('aria-expanded', 'true')
    expect(expandButton).toHaveAccessibleName('Collapse filters')
  })
})
