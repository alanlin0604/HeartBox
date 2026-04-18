import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import MoodBadge from '../MoodBadge'

// Mock LanguageContext
vi.mock('../../context/LanguageContext', () => ({
  useLang: () => ({
    t: (key) => {
      const translations = {
        'mood.positive': 'Positive',
        'mood.neutral': 'Neutral',
        'mood.negative': 'Negative',
        'mood.unknown': 'Unknown',
      }
      return translations[key] || key
    },
  }),
}))

describe('MoodBadge', () => {
  it('renders positive mood for score >= 0.2', () => {
    render(<MoodBadge score={0.5} />)
    expect(screen.getByText(/Positive/)).toBeInTheDocument()
    expect(screen.getByText(/0\.50/)).toBeInTheDocument()
  })

  it('renders neutral mood for score between -0.2 and 0.2', () => {
    render(<MoodBadge score={0.1} />)
    expect(screen.getByText(/Neutral/)).toBeInTheDocument()
    expect(screen.getByText(/0\.10/)).toBeInTheDocument()
  })

  it('renders negative mood for score < -0.2', () => {
    render(<MoodBadge score={-0.5} />)
    expect(screen.getByText(/Negative/)).toBeInTheDocument()
    expect(screen.getByText(/-0\.50/)).toBeInTheDocument()
  })

  it('renders unknown mood for null score', () => {
    render(<MoodBadge score={null} />)
    expect(screen.getByText('Unknown')).toBeInTheDocument()
    expect(screen.queryByText(/\(/)).not.toBeInTheDocument()
  })

  it('renders unknown mood for undefined score', () => {
    render(<MoodBadge score={undefined} />)
    expect(screen.getByText('Unknown')).toBeInTheDocument()
  })

  it('applies correct CSS classes for positive mood', () => {
    const { container } = render(<MoodBadge score={0.8} />)
    const badge = container.querySelector('span')
    expect(badge).toHaveClass('bg-green-500/20')
    expect(badge).toHaveClass('text-green-600')
    expect(badge).toHaveClass('border-green-500/30')
  })

  it('applies correct CSS classes for negative mood', () => {
    const { container } = render(<MoodBadge score={-0.8} />)
    const badge = container.querySelector('span')
    expect(badge).toHaveClass('bg-red-500/20')
    expect(badge).toHaveClass('text-red-600')
    expect(badge).toHaveClass('border-red-500/30')
  })

  it('formats score to 2 decimal places', () => {
    render(<MoodBadge score={0.12345} />)
    expect(screen.getByText(/0\.12/)).toBeInTheDocument()
    expect(screen.queryByText(/0\.12345/)).not.toBeInTheDocument()
  })

  it('handles edge case: exactly 0.2 is positive', () => {
    render(<MoodBadge score={0.2} />)
    expect(screen.getByText(/Positive/)).toBeInTheDocument()
  })

  it('handles edge case: exactly -0.2 is neutral', () => {
    render(<MoodBadge score={-0.2} />)
    expect(screen.getByText(/Neutral/)).toBeInTheDocument()
  })
})
