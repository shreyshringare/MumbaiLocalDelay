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

function ForecastProgress() {
  const { data: status } = useQuery({
    queryKey: ['forecast-status'],
    queryFn: api.forecastStatus,
    refetchInterval: (query) => query.state.data?.ready ? false : 5000,
  })

  const fitted = status?.fitted ?? 0
  const total = status?.total ?? 0
  const pct = total > 0 ? Math.round((fitted / total) * 100) : 0

  return (
    <div style={{ padding: '24px 0' }}>
      <p style={{ color: '#E9C46A', fontWeight: 600, marginBottom: '8px' }}>
        Computing forecasts — {fitted} / {total || '...'} stations
      </p>
      <div style={{ background: '#2a2a3e', borderRadius: '4px', height: '6px', width: '300px', marginBottom: '8px' }}>
        <div style={{ background: '#2a9d8f', width: `${pct}%`, height: '100%', borderRadius: '4px', transition: 'width 1s ease' }} />
      </div>
      <p style={{ color: '#555', fontSize: '11px' }}>
        Explore the Dashboard tab while you wait
      </p>
    </div>
  )
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
      {error && <ErrorMessage message={error instanceof Error ? error.message : String(error)} />}
      {data && isComputing(data) && (
        <ForecastProgress />
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
