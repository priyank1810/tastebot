import { expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RestaurantCard } from './RestaurantCard'

it('renders name, cuisine, budget, and location', () => {
  render(
    <RestaurantCard
      restaurant={{
        name: 'Pasta Palace', cuisine: 'italian', budget: 'mid',
        location: 'downtown', rating: 4.5, lat: null, lon: null,
      }}
    />,
  )
  expect(screen.getByText('Pasta Palace')).toBeTruthy()
  expect(screen.getByText(/italian/)).toBeTruthy()
  expect(screen.getByText(/mid/)).toBeTruthy()
  expect(screen.getByText(/downtown/)).toBeTruthy()
})
