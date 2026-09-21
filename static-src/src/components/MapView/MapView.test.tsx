import { ReactNode } from 'react'
import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapView } from './MapView'

let lastMapContainerProps: Record<string, unknown> = {}

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children, ...props }: { children: ReactNode }) => {
    lastMapContainerProps = props
    return <div data-testid="map">{children}</div>
  },
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
      onClose={() => {}}
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
      onClose={() => {}}
    />,
  )
  expect(screen.getByTestId('map')).toBeTruthy()
  expect(screen.getByText('B')).toBeTruthy()
})

it('fits the map bounds to include every geocoded pin, not just the first', () => {
  render(
    <MapView
      candidates={[
        { name: 'Near', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: 23.03, lon: 72.56 },
        { name: 'Far', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: 23.10, lon: 72.62 },
      ]}
      onClose={() => {}}
    />,
  )

  expect(lastMapContainerProps.bounds).toEqual([
    [23.03, 72.56],
    [23.10, 72.62],
  ])
})

it('calls onClose when the close button is clicked', () => {
  const onClose = vi.fn()
  render(
    <MapView
      candidates={[
        { name: 'A', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: 23.03, lon: 72.56 },
      ]}
      onClose={onClose}
    />,
  )

  screen.getByLabelText('Close map').click()
  expect(onClose).toHaveBeenCalledOnce()
})
