import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { ErrorMessage } from '../ErrorMessage'
import { LoadingSpinner } from '../LoadingSpinner'

// ── Static fintech-framed impact metrics ─────────────────────────────────────

const IMPACT_METRICS = [
  {
    label: 'Daily Pax-Hours Lost',
    value: '~45,000',
    sub: 'at Dadar CR alone (peak hours)',
    accent: '#E63946',
  },
  {
    label: 'Monsoon Productivity Cost',
    value: '₹3.75 Cr/day',
    sub: 'Jun–Sep at median Mumbai wage (₹250/hr)',
    accent: '#E9C46A',
  },
  {
    label: 'Network Cascade Strength',
    value: 'r = 0.97',
    sub: 'Dadar → Vikhroli / Thane (Pearson)',
    accent: '#A8DADC',
  },
  {
    label: 'SLA Breach Recall',
    value: '~87%',
    sub: 'Prophet 95% CI on incident days',
    accent: '#2a9d8f',
  },
]

const FINTECH_MAPPINGS = [
  { transit: 'SLA breach (delay > CI upper)', fintech: 'Circuit breaker trigger / SLA violation' },
  { transit: 'Tail-risk latency (p95 delay)', fintech: 'Value-at-Risk (VaR) / tail-risk exposure' },
  { transit: 'Cascade correlation (r = 0.97)', fintech: 'Contagion risk / desk-to-desk P&L spillover' },
  { transit: 'Peak hours (07:00–10:00)', fintech: 'Market open volatility / end-of-day settlement' },
  { transit: 'Monsoon seasonal uplift', fintech: 'Earnings season / quarter-end volume spike' },
]

// ── Component ─────────────────────────────────────────────────────────────────

function ImpactCard({ label, value, sub, accent }: typeof IMPACT_METRICS[0]) {
  return (
    <div style={{
      background: '#1e2a3e', borderRadius: '8px', padding: '14px 18px',
      borderLeft: `3px solid ${accent}`, flex: '1 1 180px',
    }}>
      <div style={{ color: accent, fontSize: '22px', fontWeight: 700, lineHeight: 1 }}>{value}</div>
      <div style={{ color: '#eaeaea', fontSize: '12px', fontWeight: 600, marginTop: '4px' }}>{label}</div>
      <div style={{ color: '#666', fontSize: '11px', marginTop: '3px' }}>{sub}</div>
    </div>
  )
}

export function InsightsTab() {
  const { data: insights, isLoading, error } = useQuery({
    queryKey: ['insights'],
    queryFn: api.insights,
    staleTime: 5 * 60 * 1000,
  })

  const [exportLoading, setExportLoading] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  async function handleExport() {
    setExportLoading(true)
    setExportError(null)
    try {
      const res = await fetch('/api/export/excel')
      if (!res.ok) throw new Error(`Export failed: ${res.status} ${res.statusText}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mumbai_local_delays_${new Date().toISOString().slice(0, 10)}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setExportError(e instanceof Error ? e.message : String(e))
    } finally {
      setExportLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '900px' }}>
      {/* ── Executive Summary ───────────────────────────────────────────────── */}
      <h3 style={{ color: '#eaeaea', marginBottom: '4px', fontSize: '16px' }}>Business Impact Summary</h3>
      <p style={{ color: '#666', fontSize: '12px', marginBottom: '16px' }}>
        Quantified cost of network latency · methods map directly to fintech operational analytics
      </p>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}

      {/* Live KPIs from API */}
      {insights && (
        <div style={{ background: '#1e2a3e', borderRadius: '8px', padding: '14px 18px', marginBottom: '16px', borderLeft: '3px solid #E9C46A' }}>
          <div style={{ color: '#E9C46A', fontSize: '11px', fontWeight: 600, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Live from DuckDB</div>
          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
            <span style={{ color: '#eaeaea', fontSize: '13px' }}>
              Highest Latency Node: <strong style={{ color: '#E63946' }}>{insights.worst_station}</strong> ({insights.worst_delay.toFixed(1)} min)
            </span>
            <span style={{ color: '#eaeaea', fontSize: '13px' }}>
              Best SLA Line: <strong style={{ color: '#2a9d8f' }}>{insights.best_line}</strong> ({insights.best_line_delay.toFixed(1)} min)
            </span>
            <span style={{ color: '#eaeaea', fontSize: '13px' }}>
              Peak Congestion: <strong style={{ color: '#A8DADC' }}>{insights.peak_window}</strong>
            </span>
            <span style={{ color: '#eaeaea', fontSize: '13px' }}>
              Pax-hrs Lost/Day: <strong style={{ color: '#E9C46A' }}>{insights.delay_hours_per_day.toLocaleString()}</strong>
            </span>
          </div>
        </div>
      )}

      {/* Static impact metrics */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '24px' }}>
        {IMPACT_METRICS.map(m => <ImpactCard key={m.label} {...m} />)}
      </div>

      {/* ── Fintech Mapping ─────────────────────────────────────────────────── */}
      <h4 style={{ color: '#eaeaea', fontSize: '14px', marginBottom: '10px', fontWeight: 600 }}>
        Analytical Patterns → Fintech Equivalents
      </h4>
      <div style={{ overflowX: 'auto', marginBottom: '24px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #444' }}>
              <th style={{ textAlign: 'left', padding: '7px 10px', color: '#E9C46A' }}>Transit Pattern</th>
              <th style={{ textAlign: 'left', padding: '7px 10px', color: '#2a9d8f' }}>Fintech Equivalent</th>
            </tr>
          </thead>
          <tbody>
            {FINTECH_MAPPINGS.map(row => (
              <tr key={row.transit} style={{ borderBottom: '1px solid #1e2a3e' }}>
                <td style={{ padding: '7px 10px', color: '#ccc' }}>{row.transit}</td>
                <td style={{ padding: '7px 10px', color: '#aaa' }}>{row.fintech}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Export ──────────────────────────────────────────────────────────── */}
      <h4 style={{ color: '#eaeaea', fontSize: '14px', marginBottom: '8px', fontWeight: 600 }}>
        Analyst Export
      </h4>
      <p style={{ color: '#666', fontSize: '12px', marginBottom: '10px' }}>
        5-sheet Excel workbook: Rankings · SLA Breach Alerts · Line Trends · Latency Heatmap · KPI Summary
      </p>
      <button
        onClick={handleExport}
        disabled={exportLoading}
        style={{
          background: exportLoading ? '#444' : '#1C3557',
          color: '#fff',
          border: '1px solid #2a9d8f',
          borderRadius: '6px',
          padding: '8px 18px',
          fontSize: '13px',
          fontWeight: 600,
          cursor: exportLoading ? 'not-allowed' : 'pointer',
        }}
      >
        {exportLoading ? 'Generating...' : 'Export to Excel (.xlsx)'}
      </button>
      {exportError && <ErrorMessage message={exportError} />}
    </div>
  )
}
