import { afterEach, describe, expect, it, vi } from 'vitest'
import { getFilterOptions, postChat } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('postChat', () => {
  it('sends session id, message, and filters in the request body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 's1', reply: 'hi', candidates: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await postChat('s1', 'hello', { cuisine: ['italian'] })

    expect(fetchMock).toHaveBeenCalledWith('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: 's1', message: 'hello', filters: { cuisine: ['italian'] } }),
    })
    expect(result.reply).toBe('hi')
  })

  it('throws when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(postChat('s1', 'hello')).rejects.toThrow('request failed with status 500')
  })
})

describe('getFilterOptions', () => {
  it('fetches from /api/filters/options', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cuisine: [], budget: [], location: [], dietary_tags: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await getFilterOptions()

    expect(fetchMock).toHaveBeenCalledWith('/api/filters/options')
  })
})
