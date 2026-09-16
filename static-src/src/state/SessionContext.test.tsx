import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SessionProvider, useSession } from './SessionContext'
import * as client from '../api/client'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

function Consumer() {
  const { messages, sendMessage, error, retryLast } = useSession()
  return (
    <div>
      <ul>
        {messages.map((m, i) => (
          <li key={i}>{m.role}: {m.content}</li>
        ))}
      </ul>
      {error && <div data-testid="error">{error}</div>}
      <button onClick={() => sendMessage('hello')}>send</button>
      <button onClick={() => retryLast()}>retry</button>
    </div>
  )
}

it('appends user and assistant messages on a successful send', async () => {
  vi.spyOn(client, 'postChat').mockResolvedValue({
    session_id: 's1', reply: 'hi there', candidates: [],
  })

  render(
    <SessionProvider>
      <Consumer />
    </SessionProvider>,
  )
  fireEvent.click(screen.getByText('send'))

  await waitFor(() => expect(screen.getByText('assistant: hi there')).toBeTruthy())
  expect(screen.getByText('user: hello')).toBeTruthy()
})

it('shows an error on failure and lets retryLast recover without duplicating the user message', async () => {
  vi.spyOn(client, 'postChat')
    .mockRejectedValueOnce(new Error('boom'))
    .mockResolvedValueOnce({ session_id: 's1', reply: 'recovered', candidates: [] })

  render(
    <SessionProvider>
      <Consumer />
    </SessionProvider>,
  )
  fireEvent.click(screen.getByText('send'))

  await waitFor(() => expect(screen.getByTestId('error')).toBeTruthy())
  expect(screen.getAllByText('user: hello')).toHaveLength(1)

  fireEvent.click(screen.getByText('retry'))

  await waitFor(() => expect(screen.getByText('assistant: recovered')).toBeTruthy())
  expect(screen.getAllByText('user: hello')).toHaveLength(1)
})
