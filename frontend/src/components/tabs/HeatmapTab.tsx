import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'
import { darkLayout } from '../darkLayout'

const STATIONS = ['Dadar CR', 'CSMT', 'Thane', 'Kalyan', 'Panvel', 'Borivali', 'Andheri', 'Bandra', 'Kurla', 'Dombivli']

export function HeatmapTab() {
  const [station, setStation] = useState(STATIONS[0])
  const { data, isLoading, error } = useQuery({
    queryKey: ['heatmap', station],
    queryFn: () => api.heatmap(station),
  })

  return (
    <div>
      <div style={{ marginBottom: '12px' }}>
        <label style={{ color: '#eaeaea', marginRight: '8px' }}>Station:</label>
        <select
          value={station}
          onChange={e => setStation(e.target.value)}
          style={{ background: '#2a2a3e', color: '#eaeaea', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px' }}
        >
          {STATIONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && (
        <Plot
          data={[{
            type: 'heatmap',
            z: data.matrix,
            colorscale: [[0, '#2a9d8f'], [0.5, '#e9c46a'], [1, '#e63946']] as [number, string][],
            colorbar: { title: { text: 'Avg Latency (min)' } },
          }]}
          layout={{
            ...darkLayout,
            title: { text: `Latency Heatmap — ${data.station}` },
            xaxis: { ...darkLayout.xaxis, title: { text: 'Hour of Day' } },
            yaxis: {
              ...darkLayout.yaxis,
              title: { text: 'Day of Week' },
              tickvals: [0, 1, 2, 3, 4, 5, 6],
              ticktext: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            },
          }}
          style={{ width: '100%', height: '400px' }}
          config={{ responsive: true, displayModeBar: false }}
        />
      )}
    </div>
  )
}
