interface Props { message: string }

export function ErrorMessage({ message }: Props) {
  return (
    <div style={{ padding: '16px', background: '#2a1515', borderRadius: '8px', color: '#E63946' }}>
      <strong>Error:</strong> {message}
    </div>
  )
}
