import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api, type ForecastPoint } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'
import { darkLayout } from '../darkLayout'

const STATIONS = ['Dadar CR', 'CSMT', 'Thane', 'Kalyan', 'Panvel', 'Borivali', 'Andheri']

type ComputingStatus = { status: string }

function isComputing(data: ForecastPoint[] | ComputingStatus): data is ComputingStatus {
  return !Array.isArray(data)
}

export function PredictionTab() {
  const [station, setStation] = useState(STATIONS[0])

  const { data, isLoading, error } = useQuery({
    queryKey: ['forecast', station],
    queryFn: () => api.forecast(station),
    refetchInterval: (query) => {
      const d = query.state.data
      return d && isComputing(d) ? 3000 : false
    },
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
      {data && isComputing(data) && (
        <p style={{ color: '#E9C46A', padding: '16px' }}>Prophet model computing... auto-refreshing</p>
      )}
      {data && !isComputing(data) && (
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines',
              name: 'Forecast',
              x: data.map(d => d.ds),
              y: data.map(d => d.yhat),
              line: { color: '#E9C46A' },
            },
            {
              type: 'scatter',
              mode: 'lines',
              name: 'Upper CI',
              x: data.map(d => d.ds),
              y: data.map(d => d.yhat_upper),
              line: { color: '#E9C46A', dash: 'dot', width: 1 },
              showlegend: false,
            },
            {
              type: 'scatter',
              mode: 'lines',
              name: 'Lower CI',
              x: data.map(d => d.ds),
              y: data.map(d => d.yhat_lower),
              fill: 'tonexty',
              fillcolor: 'rgba(233,196,106,0.15)',
              line: { color: '#E9C46A', dash: 'dot', width: 1 },
              showlegend: false,
            },
          ]}
          layout={{
            ...darkLayout,
            title: { text: `7-Day Forecast — ${station}` },
            yaxis: { ...darkLayout.yaxis, title: { text: 'Predicted Delay (min)' } },
          }}
          style={{ width: '100%', height: '400px' }}
          config={{ responsive: true, displayModeBar: false }}
        />
      )}
    </div>
  )
}
