import { expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ChatInput } from './ChatInput'

it('calls onSend with the trimmed input and clears the field', () => {
  const onSend = vi.fn()
  render(<ChatInput onSend={onSend} />)

  const input = screen.getByPlaceholderText('Ask for a restaurant...') as HTMLInputElement
  fireEvent.change(input, { target: { value: '  cheap pizza  ' } })
  fireEvent.click(screen.getByText('Send'))

  expect(onSend).toHaveBeenCalledWith('cheap pizza')
  expect(input.value).toBe('')
})

it('does not call onSend for empty/whitespace-only input', () => {
  const onSend = vi.fn()
  render(<ChatInput onSend={onSend} />)

  fireEvent.click(screen.getByText('Send'))

  expect(onSend).not.toHaveBeenCalled()
})
