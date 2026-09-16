import { ReactNode } from 'react'
import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapView } from './MapView'

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

it('renders nothing when no candidates have coordinates', () => {
  const { container } = render(
    <MapView
      candidates={[
        { name: 'A', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: null, lon: null },
      ]}
    />,
  )
  expect(container.firstChild).toBeNull()
})

it('renders a map with a marker per geocoded candidate', () => {
  render(
    <MapView
      candidates={[
        { name: 'A', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: null, lon: null },
        { name: 'B', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: 23.03, lon: 72.56 },
      ]}
    />,
  )
  expect(screen.getByTestId('map')).toBeTruthy()
  expect(screen.getByText('B')).toBeTruthy()
})
