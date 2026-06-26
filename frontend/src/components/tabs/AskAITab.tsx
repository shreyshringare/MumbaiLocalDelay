import { useState } from 'react'
import { ErrorMessage } from '../ErrorMessage'

interface AskResponse {
  question: string
  sql: string
  answer: string
}

export function AskAITab() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AskResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return
    setIsLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      if (!data.ok) {
        const err = await data.json() as { detail?: string }
        throw new Error(err.detail ?? `${data.status}`)
      }
      setResult(await data.json() as AskResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }

  const examples = [
    'Which station has the highest tail-risk latency (p95) on Central line?',
    'What are the top 5 worst SLA compliance stations during morning peak?',
    'How does Monday compare to Sunday for average latency?',
    'Which stations breach the 8-minute latency threshold during morning peak?',
    'Show week-over-week latency change for Western line this year.',
  ]

  return (
    <div style={{ maxWidth: '800px' }}>
      <h3 style={{ color: '#eaeaea', marginBottom: '8px', fontSize: '16px' }}>
        Ask AI — Natural Language Analytics Interface
      </h3>
      <p style={{ color: '#888', fontSize: '13px', marginBottom: '16px' }}>
        Plain-English question → Claude generates DuckDB SQL → live result. Analyst self-serve without writing SQL.
      </p>

      <form onSubmit={handleSubmit} style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Which station has the worst Monday morning delays?"
            style={{
              flex: 1,
              background: '#2a2a3e',
              color: '#eaeaea',
              border: '1px solid #444',
              borderRadius: '4px',
              padding: '8px 12px',
              fontSize: '14px',
            }}
          />
          <button
            type="submit"
            disabled={isLoading || !question.trim()}
            style={{
              background: '#E9C46A',
              color: '#1a1a2e',
              border: 'none',
              borderRadius: '4px',
              padding: '8px 16px',
              fontWeight: 700,
              cursor: isLoading ? 'wait' : 'pointer',
              fontSize: '14px',
            }}
          >
            {isLoading ? 'Thinking...' : 'Ask'}
          </button>
        </div>
      </form>

      {/* Example questions */}
      <div style={{ marginBottom: '16px' }}>
        <p style={{ color: '#666', fontSize: '12px', marginBottom: '6px' }}>Examples:</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {examples.map(ex => (
            <button
              key={ex}
              onClick={() => setQuestion(ex)}
              style={{
                background: '#1e2a3e',
                color: '#aaa',
                border: '1px solid #333',
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {result && (
        <div>
          <div style={{ background: '#1e2a3e', borderRadius: '6px', padding: '12px', marginBottom: '12px' }}>
            <p style={{ color: '#666', fontSize: '11px', marginBottom: '4px' }}>Generated SQL:</p>
            <pre style={{ color: '#E9C46A', fontSize: '12px', overflow: 'auto', margin: 0 }}>
              {result.sql}
            </pre>
          </div>
          <div style={{ background: '#1e2a3e', borderRadius: '6px', padding: '12px' }}>
            <p style={{ color: '#666', fontSize: '11px', marginBottom: '4px' }}>Result:</p>
            <pre style={{ color: '#eaeaea', fontSize: '13px', overflow: 'auto', margin: 0, whiteSpace: 'pre-wrap' }}>
              {result.answer}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
