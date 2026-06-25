import { useState } from 'react'
import { ErrorMessage } from '../ErrorMessage'

export function InsightsTab() {
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
      a.download = `mumbai_local_delays_${new Date().toISOString().slice(0, 10)}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h3 style={{ color: '#eaeaea', marginBottom: '16px', fontSize: '16px' }}>Business Insights</h3>
      <p style={{ color: '#888', fontSize: '13px', marginBottom: '16px' }}>
        KPI summary has moved to the Dashboard tab. Export the full analytics workbook below.
      </p>
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
        }}
      >
        {loading ? 'Generating...' : 'Export to Excel (.xlsx)'}
      </button>
      {error && <ErrorMessage message={error} />}
    </div>
  )
}
