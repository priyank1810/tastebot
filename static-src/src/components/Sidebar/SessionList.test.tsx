import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SessionList } from './SessionList'
import { SessionProvider } from '../../state/SessionContext'
import * as client from '../../api/client'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})

it('lists sessions and opens one on click', async () => {
  vi.spyOn(client, 'getSessions').mockResolvedValue([
    { id: 'abc', title: 'Cheap pizza', created_at: '2026-01-01T00:00:00' },
  ])
  vi.spyOn(client, 'getSessionMessages').mockResolvedValue([{ role: 'user', content: 'hi' }])

  render(
    <SessionProvider>
      <SessionList />
    </SessionProvider>,
  )

  await waitFor(() => expect(screen.getByText('Cheap pizza')).toBeTruthy())

  fireEvent.click(screen.getByText('Cheap pizza'))

  await waitFor(() => expect(client.getSessionMessages).toHaveBeenCalledWith('abc'))
})
