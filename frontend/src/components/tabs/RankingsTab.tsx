import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'
import { darkLayout } from '../darkLayout'

const LINES = ['Central', 'Western', 'Harbour']
const PERIODS = ['morning_peak', 'evening_peak', 'off_peak']

export function RankingsTab() {
  const [line, setLine] = useState(LINES[0])
  const [period, setPeriod] = useState(PERIODS[0])

  const { data, isLoading, error } = useQuery({
    queryKey: ['rankings', line, period],
    queryFn: () => api.rankings(line, period),
  })

  return (
    <div>
      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <div>
          <label style={{ color: '#eaeaea', marginRight: '8px' }}>Line:</label>
          <select
            value={line}
            onChange={e => setLine(e.target.value)}
            style={{ background: '#2a2a3e', color: '#eaeaea', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px' }}
          >
            {LINES.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
        <div>
          <label style={{ color: '#eaeaea', marginRight: '8px' }}>Period:</label>
          <select
            value={period}
            onChange={e => setPeriod(e.target.value)}
            style={{ background: '#2a2a3e', color: '#eaeaea', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px' }}
          >
            {PERIODS.map(p => <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
      </div>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && (
        <Plot
          data={[{
            type: 'bar',
            x: data.map(d => d.station_name),
            y: data.map(d => d.avg_delay),
            error_y: {
              type: 'data',
              symmetric: false,
              array: data.map(d => d.ci_upper != null ? d.ci_upper - d.avg_delay : 0),
              arrayminus: data.map(d => d.ci_lower != null ? d.avg_delay - d.ci_lower : 0),
            },
            marker: { color: '#E63946' },
          }]}
          layout={{
            ...darkLayout,
            title: { text: `${line} Line — Station Latency Rankings (${period.replace(/_/g, ' ')})` },
            yaxis: { ...darkLayout.yaxis, title: { text: 'Avg Latency (min)' } },
          }}
          style={{ width: '100%', height: '400px' }}
          config={{ responsive: true, displayModeBar: false }}
        />
      )}
    </div>
  )
}
