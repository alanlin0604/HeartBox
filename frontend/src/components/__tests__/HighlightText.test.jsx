import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import HighlightText from '../HighlightText'

describe('HighlightText', () => {
  it('renders text without highlighting when no keyword provided', () => {
    const { container } = render(<HighlightText text="Hello world" keyword="" />)
    expect(container).toHaveTextContent('Hello world')
    expect(container.querySelector('mark')).not.toBeInTheDocument()
  })

  it('highlights matching keyword in text', () => {
    render(<HighlightText text="Hello world" keyword="world" />)
    const mark = screen.getByText('world')
    expect(mark.tagName).toBe('MARK')
    expect(mark).toHaveClass('bg-yellow-300/40')
  })

  it('highlights multiple occurrences of keyword', () => {
    const { container } = render(
      <HighlightText text="test test test" keyword="test" />
    )
    const marks = container.querySelectorAll('mark')
    expect(marks).toHaveLength(3)
  })

  it('is case insensitive', () => {
    render(<HighlightText text="Hello WORLD world" keyword="world" />)
    const marks = screen.getAllByText(/world/i)
    expect(marks).toHaveLength(2)
    marks.forEach(mark => {
      expect(mark.tagName).toBe('MARK')
    })
  })

  it('escapes regex special characters in keyword', () => {
    const { container } = render(
      <HighlightText text="Price is $100" keyword="$100" />
    )
    const mark = screen.getByText('$100')
    expect(mark.tagName).toBe('MARK')
  })

  it('handles parentheses in keyword', () => {
    render(<HighlightText text="function(args)" keyword="(args)" />)
    const mark = screen.getByText('(args)')
    expect(mark.tagName).toBe('MARK')
  })

  it('handles brackets in keyword', () => {
    render(<HighlightText text="array[0]" keyword="[0]" />)
    const mark = screen.getByText('[0]')
    expect(mark.tagName).toBe('MARK')
  })

  it('trims whitespace from keyword', () => {
    render(<HighlightText text="Hello world" keyword="  world  " />)
    const mark = screen.getByText('world')
    expect(mark.tagName).toBe('MARK')
  })

  it('returns text as-is when keyword is only whitespace', () => {
    const { container } = render(<HighlightText text="Hello world" keyword="   " />)
    expect(container).toHaveTextContent('Hello world')
    expect(container.querySelector('mark')).not.toBeInTheDocument()
  })

  it('handles empty text', () => {
    const { container } = render(<HighlightText text="" keyword="test" />)
    expect(container.textContent).toBe('')
  })

  it('preserves non-matching parts as regular spans', () => {
    const { container } = render(<HighlightText text="Hello world" keyword="world" />)
    const spans = container.querySelectorAll('span')
    expect(spans.length).toBeGreaterThan(0)
  })

  it('handles partial word matches', () => {
    render(<HighlightText text="testing" keyword="test" />)
    const mark = screen.getByText('test')
    expect(mark.tagName).toBe('MARK')
  })
})
