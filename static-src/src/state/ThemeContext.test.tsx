import { afterEach, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider, useTheme } from './ThemeContext'

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.className = ''
})

function Consumer() {
  const { theme, toggleTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={toggleTheme}>toggle</button>
    </div>
  )
}

it('defaults to dark and toggles to light', () => {
  render(
    <ThemeProvider>
      <Consumer />
    </ThemeProvider>,
  )
  expect(screen.getByTestId('theme').textContent).toBe('dark')
  expect(document.documentElement.classList.contains('dark')).toBe(true)

  fireEvent.click(screen.getByText('toggle'))

  expect(screen.getByTestId('theme').textContent).toBe('light')
  expect(document.documentElement.classList.contains('dark')).toBe(false)
})
