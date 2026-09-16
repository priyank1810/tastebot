import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import App from './App'
import * as client from './api/client'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})

it('renders the chat shell without crashing', async () => {
  vi.spyOn(client, 'getSessions').mockResolvedValue([])
  vi.spyOn(client, 'getFilterOptions').mockResolvedValue({
    cuisine: [], budget: [], location: [], dietary_tags: [],
  })

  render(<App />)

  expect(screen.getByText('🍽️ Restaurant Recommendation Bot')).toBeTruthy()
  expect(screen.getByPlaceholderText('Ask for a restaurant...')).toBeTruthy()
})
