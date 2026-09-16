import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { RestaurantCandidate } from '../../api/client'

type GeocodedCandidate = RestaurantCandidate & { lat: number; lon: number }

export function MapView({ candidates }: { candidates: RestaurantCandidate[] }) {
  const pins = candidates.filter(
    (c): c is GeocodedCandidate => c.lat != null && c.lon != null,
  )

  if (pins.length === 0) return null

  const center: [number, number] = [pins[0].lat, pins[0].lon]

  return (
    <div className="h-64 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
      <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {pins.map((p) => (
          <Marker key={p.name} position={[p.lat, p.lon]}>
            <Popup>{p.name}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
