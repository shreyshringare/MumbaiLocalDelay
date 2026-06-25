import { useQuery } from '@tanstack/react-query'
import { api, type AnomalyEntry } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

const SEVERITY_COLOR: Record<string, string> = {
  high: '#E63946',
  medium: '#E9C46A',
  low: '#2a9d8f',
}

function AnomalyCard({ entry }: { entry: AnomalyEntry }) {
  const color = SEVERITY_COLOR[entry.severity.toLowerCase()] ?? '#888'
  return (
    <div style={{ background: '#1e2a3e', borderLeft: `4px solid ${color}`, borderRadius: '6px', padding: '12px', marginBottom: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <strong style={{ color, fontSize: '15px' }}>{entry.station}</strong>
        <span style={{ color: '#888', fontSize: '12px' }}>{entry.date}</span>
      </div>
      <div style={{ color: '#ccc', fontSize: '13px' }}>
        <span>Actual: <strong style={{ color: '#E63946' }}>{entry.actual.toFixed(1)} min</strong></span>
        {' · '}
        <span>Expected: {entry.expected.toFixed(1)} min</span>
        {' · '}
        <span>Severity: <strong style={{ color }}>{entry.severity}</strong></span>
      </div>
    </div>
  )
}

export function AnomalyTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['anomalies'],
    queryFn: api.anomalies,
  })

  return (
    <div>
      <h3 style={{ color: '#eaeaea', marginBottom: '12px', fontSize: '16px' }}>Anomaly Alerts — Prophet 95% CI</h3>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && data.length === 0 && <p style={{ color: '#888' }}>No anomalies detected.</p>}
      {data && data.map((entry, i) => <AnomalyCard key={i} entry={entry} />)}
    </div>
  )
}
