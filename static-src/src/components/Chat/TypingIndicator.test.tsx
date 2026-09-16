import { expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TypingIndicator } from './TypingIndicator'

it('renders a typing indicator', () => {
  render(<TypingIndicator />)
  expect(screen.getByLabelText('Assistant is typing')).toBeTruthy()
})
