import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ConfirmModal from '../ConfirmModal'

describe('ConfirmModal', () => {
  const defaultProps = {
    open: true,
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  }

  it('renders modal when open is true', () => {
    render(<ConfirmModal {...defaultProps} />)
    expect(screen.getByText('Confirm Action')).toBeInTheDocument()
    expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument()
  })

  it('does not render modal when open is false', () => {
    render(<ConfirmModal {...defaultProps} open={false} />)
    expect(screen.queryByText('Confirm Action')).not.toBeInTheDocument()
  })

  it('calls onConfirm when confirm button is clicked', () => {
    const onConfirm = vi.fn()
    render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />)

    fireEvent.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn()
    render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)

    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when Escape key is pressed', () => {
    const onCancel = vi.fn()
    render(<ConfirmModal {...defaultProps} onCancel={onCancel} />)

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('disables buttons when loading is true', () => {
    render(<ConfirmModal {...defaultProps} loading={true} />)

    const confirmButton = screen.getByText('...')
    const cancelButton = screen.getByText('Cancel')

    expect(confirmButton).toBeDisabled()
    expect(cancelButton).toBeDisabled()
  })

  it('shows loading text on confirm button when loading', () => {
    render(<ConfirmModal {...defaultProps} loading={true} />)
    expect(screen.getByText('...')).toBeInTheDocument()
    expect(screen.queryByText('Confirm')).not.toBeInTheDocument()
  })

  it('has correct ARIA attributes', () => {
    const { container } = render(<ConfirmModal {...defaultProps} />)
    const dialog = container.querySelector('[role="dialog"]')

    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveAttribute('aria-labelledby', 'confirm-modal-title')
  })

  it('renders title with correct id for ARIA', () => {
    render(<ConfirmModal {...defaultProps} />)
    const title = screen.getByText('Confirm Action')

    expect(title).toHaveAttribute('id', 'confirm-modal-title')
    expect(title.tagName).toBe('H3')
  })

  it('applies correct CSS classes to buttons', () => {
    render(<ConfirmModal {...defaultProps} />)

    const confirmButton = screen.getByText('Confirm')
    const cancelButton = screen.getByText('Cancel')

    expect(confirmButton).toHaveClass('btn-danger')
    expect(cancelButton).toHaveClass('btn-secondary')
  })

  it('renders custom button texts', () => {
    render(
      <ConfirmModal
        {...defaultProps}
        confirmText="Delete Forever"
        cancelText="Keep It"
      />
    )

    expect(screen.getByText('Delete Forever')).toBeInTheDocument()
    expect(screen.getByText('Keep It')).toBeInTheDocument()
  })

  it('renders custom title and message', () => {
    render(
      <ConfirmModal
        {...defaultProps}
        title="Delete Item"
        message="This action cannot be undone."
      />
    )

    expect(screen.getByText('Delete Item')).toBeInTheDocument()
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument()
  })
})
