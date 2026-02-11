import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EmptyState from '../EmptyState'

describe('EmptyState', () => {
  it('renders title and description from props', () => {
    render(
      <EmptyState
        title="No notes yet"
        description="Start writing your first mood entry."
      />
    )

    expect(screen.getByText('No notes yet')).toBeInTheDocument()
    expect(screen.getByText('Start writing your first mood entry.')).toBeInTheDocument()
  })

  it('renders the action button when actionText and onAction are provided', () => {
    const onAction = vi.fn()
    render(
      <EmptyState
        title="No notes yet"
        description="Start writing your first mood entry."
        actionText="Create Note"
        onAction={onAction}
      />
    )

    const button = screen.getByRole('button', { name: 'Create Note' })
    expect(button).toBeInTheDocument()

    fireEvent.click(button)
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('does not render the action button when actionText or onAction is missing', () => {
    const { rerender } = render(
      <EmptyState
        title="Empty"
        description="Nothing here."
        actionText="Click me"
      />
    )

    // No onAction provided - button should not appear
    expect(screen.queryByRole('button')).not.toBeInTheDocument()

    // Provide onAction but no actionText - button should still not appear
    rerender(
      <EmptyState
        title="Empty"
        description="Nothing here."
        onAction={vi.fn()}
      />
    )
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
