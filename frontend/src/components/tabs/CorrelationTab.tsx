import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'
import { darkLayout } from '../darkLayout'

const LINES = ['Central', 'Western', 'Harbour']

export function CorrelationTab() {
  const [line, setLine] = useState(LINES[0])
  const { data, isLoading, error } = useQuery({
    queryKey: ['correlation', line],
    queryFn: () => api.correlation(line),
  })

  return (
    <div>
      <div style={{ marginBottom: '12px' }}>
        <label style={{ color: '#eaeaea', marginRight: '8px' }}>Line:</label>
        <select
          value={line}
          onChange={e => setLine(e.target.value)}
          style={{ background: '#2a2a3e', color: '#eaeaea', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px' }}
        >
          {LINES.map(l => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && (
        <Plot
          data={[{
            type: 'heatmap',
            z: data.matrix,
            x: data.stations,
            y: data.stations,
            colorscale: 'RdBu',
            zmin: -1,
            zmax: 1,
            colorbar: { title: { text: 'Pearson r' } },
          }]}
          layout={{
            ...darkLayout,
            title: { text: `Station Co-Delay Correlation — ${line}` },
          }}
          style={{ width: '100%', height: '500px' }}
          config={{ responsive: true, displayModeBar: false }}
        />
      )}
    </div>
  )
}
