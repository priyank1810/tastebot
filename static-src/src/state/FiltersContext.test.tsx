import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { FiltersProvider, useFilters } from './FiltersContext'
import * as client from '../api/client'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function Consumer() {
  const { options, selected, toggleValue } = useFilters()
  return (
    <div>
      <div data-testid="cuisines">{options.cuisine.join(',')}</div>
      <div data-testid="selected">{(selected.cuisine ?? []).join(',')}</div>
      <button onClick={() => toggleValue('cuisine', 'italian')}>toggle italian</button>
    </div>
  )
}

it('loads options on mount and toggles a selection on and off', async () => {
  vi.spyOn(client, 'getFilterOptions').mockResolvedValue({
    cuisine: ['italian', 'gujarati'], budget: [], location: [], dietary_tags: [],
  })

  render(
    <FiltersProvider>
      <Consumer />
    </FiltersProvider>,
  )

  await waitFor(() => expect(screen.getByTestId('cuisines').textContent).toBe('italian,gujarati'))

  fireEvent.click(screen.getByText('toggle italian'))
  expect(screen.getByTestId('selected').textContent).toBe('italian')

  fireEvent.click(screen.getByText('toggle italian'))
  expect(screen.getByTestId('selected').textContent).toBe('')
})
