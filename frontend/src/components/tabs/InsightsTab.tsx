import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

function ExportButton() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleExport() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/export/excel')
      if (!res.ok) throw new Error(`Export failed: ${res.status} ${res.statusText}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const today = new Date().toISOString().slice(0, 10)
      a.download = `mumbai_local_delays_${today}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ marginBottom: '16px' }}>
      <button
        onClick={handleExport}
        disabled={loading}
        style={{
          background: loading ? '#444' : '#1C3557',
          color: '#fff',
          border: '1px solid #2a9d8f',
          borderRadius: '6px',
          padding: '8px 18px',
          fontSize: '13px',
          fontWeight: 600,
          cursor: loading ? 'not-allowed' : 'pointer',
          letterSpacing: '0.02em',
        }}
      >
        {loading ? 'Generating...' : 'Export to Excel (.xlsx)'}
      </button>
      {error && <span style={{ color: '#E63946', fontSize: '12px', marginLeft: '12px' }}>{error}</span>}
    </div>
  )
}

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
      <ExportButton />
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={error instanceof Error ? error.message : String(error)} />}
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
