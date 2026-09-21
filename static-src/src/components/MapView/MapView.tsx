import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { RestaurantCandidate } from '../../api/client'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Vite doesn't resolve Leaflet's default icon URLs (they assume a bundler
// that keeps images next to the CSS), so markers render broken without this.
delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

type GeocodedCandidate = RestaurantCandidate & { lat: number; lon: number }

export function MapView({ candidates }: { candidates: RestaurantCandidate[] }) {
  const pins = candidates.filter(
    (c): c is GeocodedCandidate => c.lat != null && c.lon != null,
  )

  if (pins.length === 0) return null

  const bounds: [number, number][] = pins.map((p) => [p.lat, p.lon])

  return (
    <div className="h-64 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
      <MapContainer
        bounds={bounds}
        boundsOptions={{ padding: [20, 20], maxZoom: 15 }}
        style={{ height: '100%', width: '100%' }}
      >
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
