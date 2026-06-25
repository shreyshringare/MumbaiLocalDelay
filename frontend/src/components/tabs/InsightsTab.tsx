import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

interface KpiChipProps {
  label: string
  value: string
  detail: string
  accent: string
}

function KpiChip({ label, value, detail, accent }: KpiChipProps) {
  return (
    <div style={{ background: '#1e2a3e', borderRadius: '8px', padding: '12px 16px', minWidth: '180px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{ color: accent, fontSize: '20px', fontWeight: 700 }}>{value}</span>
        <span style={{ color: '#eaeaea', fontSize: '13px' }}>{label}</span>
      </div>
      <p style={{ color: '#888', fontSize: '11px', margin: '4px 0 0 0' }}>{detail}</p>
    </div>
  )
}

export function InsightsTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['insights'],
    queryFn: api.insights,
  })

  return (
    <div>
      <h3 style={{ color: '#eaeaea', marginBottom: '16px', fontSize: '16px' }}>Business Insights</h3>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && (
        <>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '20px' }}>
            <KpiChip
              label="Worst Station"
              value={data.worst_station}
              detail={`${data.worst_delay.toFixed(1)} min avg delay`}
              accent="#E63946"
            />
            <KpiChip
              label="Best Line"
              value={data.best_line}
              detail={`${data.best_line_delay.toFixed(1)} min avg delay`}
              accent="#2a9d8f"
            />
            <KpiChip
              label="Passenger-Hours Lost/Day"
              value={data.delay_hours_per_day.toLocaleString()}
              detail="CI: [35,000–58,000] at ±20% uncertainty"
              accent="#E9C46A"
            />
            <KpiChip
              label="Peak Window"
              value={data.peak_window}
              detail="Highest delay period"
              accent="#A8DADC"
            />
          </div>
          <p style={{ color: '#ccc', fontSize: '13px', lineHeight: 1.6 }}>
            Passenger-hours calculation: 15 trains/hr × 1,000 passengers × avg delay / 60 × 30 stations.
            Confidence interval: ±20% uncertainty on passenger load (MCRC estimate).
          </p>
        </>
      )}
    </div>
  )
}
