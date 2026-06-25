import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

export function QualityTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['quality'],
    queryFn: api.quality,
  })

  return (
    <div>
      <h3 style={{ color: '#eaeaea', marginBottom: '12px', fontSize: '16px' }}>Data Quality</h3>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #444' }}>
                {['Station', 'Rows', 'Unique Dates', 'Last Updated'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '8px', color: '#E9C46A' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map(row => (
                <tr key={row.station_name} style={{ borderBottom: '1px solid #2a2a3e' }}>
                  <td style={{ padding: '6px 8px', color: '#eaeaea' }}>{row.station_name}</td>
                  <td style={{ padding: '6px 8px', color: '#aaa' }}>{row.row_count.toLocaleString()}</td>
                  <td style={{ padding: '6px 8px', color: '#aaa' }}>{row.unique_dates}</td>
                  <td style={{ padding: '6px 8px', color: '#aaa' }}>{row.last_updated ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
