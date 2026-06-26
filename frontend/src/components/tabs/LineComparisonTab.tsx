import { useQuery } from '@tanstack/react-query'
import Plot from 'react-plotly.js'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'
import { darkLayout } from '../darkLayout'

const LINE_COLORS = ['#E63946', '#2a9d8f', '#E9C46A'] as const

export function LineComparisonTab() {
  const central = useQuery({ queryKey: ['line-trend', 'Central'], queryFn: () => api.lineTrend('Central') })
  const western = useQuery({ queryKey: ['line-trend', 'Western'], queryFn: () => api.lineTrend('Western') })
  const harbour = useQuery({ queryKey: ['line-trend', 'Harbour'], queryFn: () => api.lineTrend('Harbour') })

  const isLoading = central.isLoading || western.isLoading || harbour.isLoading
  const firstError = central.error ?? western.error ?? harbour.error

  return (
    <div>
      {isLoading && <LoadingSpinner />}
      {firstError && <ErrorMessage message={firstError instanceof Error ? firstError.message : String(firstError)} />}
      {!isLoading && !firstError && (
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines',
              name: 'Central',
              x: central.data?.map(d => d.date) ?? [],
              y: central.data?.map(d => d.avg_delay) ?? [],
              line: { color: LINE_COLORS[0], width: 2 },
            },
            {
              type: 'scatter',
              mode: 'lines',
              name: 'Western',
              x: western.data?.map(d => d.date) ?? [],
              y: western.data?.map(d => d.avg_delay) ?? [],
              line: { color: LINE_COLORS[1], width: 2 },
            },
            {
              type: 'scatter',
              mode: 'lines',
              name: 'Harbour',
              x: harbour.data?.map(d => d.date) ?? [],
              y: harbour.data?.map(d => d.avg_delay) ?? [],
              line: { color: LINE_COLORS[2], width: 2 },
            },
          ]}
          layout={{
            ...darkLayout,
            title: { text: '30-Day Latency Comparison by Line' },
            yaxis: { ...darkLayout.yaxis, title: { text: 'Avg Latency (min)' } },
            legend: { bgcolor: '#1e2a3e', bordercolor: '#333' },
          }}
          style={{ width: '100%', height: '400px' }}
          config={{ responsive: true, displayModeBar: false }}
        />
      )}
    </div>
  )
}
