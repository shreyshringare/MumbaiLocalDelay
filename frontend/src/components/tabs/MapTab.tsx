import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { api, type StationDelay } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

function delayColor(avgDelay: number): string {
  if (avgDelay < 3) return '#2a9d8f'
  if (avgDelay < 6) return '#E9C46A'
  return '#E63946'
}

export function MapTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['map-data'],
    queryFn: api.mapData,
    staleTime: 5 * 60 * 1000,
  })

  const stations = data?.filter(
    (s): s is StationDelay & { latitude: number; longitude: number } =>
      s.latitude !== null && s.longitude !== null
  ) ?? []

  return (
    <div>
      <h3 style={{ color: '#eaeaea', marginBottom: '12px', fontSize: '16px' }}>
        Station Map — Delay Severity
      </h3>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={error instanceof Error ? error.message : String(error)} />}
      {!isLoading && !error && (
        <div style={{ height: '500px', borderRadius: '8px', overflow: 'hidden' }}>
          <MapContainer
            center={[19.076, 72.877]}
            zoom={11}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            {stations.map(station => (
              <CircleMarker
                key={station.station_name}
                center={[station.latitude, station.longitude]}
                radius={8}
                pathOptions={{
                  color: delayColor(station.avg_delay),
                  fillColor: delayColor(station.avg_delay),
                  fillOpacity: 0.8,
                  weight: 1,
                }}
              >
                <Popup>
                  <strong>{station.station_name}</strong>
                  <br />
                  Line: {station.line}
                  <br />
                  Avg delay: {station.avg_delay.toFixed(1)} min
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      )}
      <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '12px', color: '#888' }}>
        <span><span style={{ color: '#2a9d8f' }}>●</span> &lt;3 min</span>
        <span><span style={{ color: '#E9C46A' }}>●</span> 3–6 min</span>
        <span><span style={{ color: '#E63946' }}>●</span> &gt;6 min</span>
      </div>
    </div>
  )
}
