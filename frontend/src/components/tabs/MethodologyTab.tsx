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
      {data && Object.entries(data).map(([section, content]) => {
        const item = content as { title?: string; content?: string } | string
        const title = typeof item === 'object' && item.title ? item.title : section
        const body = typeof item === 'object' && item.content ? item.content : String(item)
        return (
          <div key={section} style={{ marginBottom: '20px' }}>
            <h4 style={{ color: '#E9C46A', marginBottom: '8px' }}>{title}</h4>
            <p style={{ color: '#ccc', fontSize: '13px', lineHeight: '1.6' }}>{body}</p>
          </div>
        )
      })}
    </div>
  )
}
