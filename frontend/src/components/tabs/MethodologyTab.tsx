import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

export function MethodologyTab() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['methodology'],
    queryFn: api.methodology,
  })

  return (
    <div style={{ maxWidth: '800px' }}>
      <h3 style={{ color: '#eaeaea', marginBottom: '16px' }}>Data Methodology</h3>
      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={(error as Error).message} />}
      {data && Object.entries(data).map(([section, content]) => (
        <div key={section} style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#E9C46A', marginBottom: '8px' }}>{section}</h4>
          {Array.isArray(content)
            ? (content as unknown[]).map((item, i) => (
                <p key={i} style={{ color: '#ccc', fontSize: '13px', margin: '4px 0' }}>{String(item)}</p>
              ))
            : <p style={{ color: '#ccc', fontSize: '13px' }}>{String(content)}</p>
          }
        </div>
      ))}
    </div>
  )
}
