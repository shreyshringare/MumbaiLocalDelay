import { useState } from 'react'

const TABS = [
  { id: 'map', label: 'Station Map' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'rankings', label: 'Rankings' },
  { id: 'anomaly', label: 'Anomaly Alerts' },
  { id: 'lines', label: 'Line Comparison' },
  { id: 'quality', label: 'Data Quality' },
  { id: 'insights', label: 'Business Insights' },
  { id: 'prediction', label: 'Prediction' },
  { id: 'correlation', label: 'Correlation' },
  { id: 'methodology', label: 'Methodology' },
] as const

type TabId = (typeof TABS)[number]['id']

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('map')

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '16px' }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <h1 style={{ color: '#E9C46A', fontSize: '22px', fontWeight: 700 }}>
          Mumbai Local Train Delay Visualizer
        </h1>
        <p style={{ color: '#888', fontSize: '13px', marginTop: '4px' }}>
          Simulated delays calibrated on real Indian Railways data · Prophet forecast · 120+ stations
        </p>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '16px', borderBottom: '1px solid #333', paddingBottom: '8px' }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '6px 14px',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '13px',
              background: activeTab === tab.id ? '#E9C46A' : '#2a2a3e',
              color: activeTab === tab.id ? '#1a1a2e' : '#eaeaea',
              fontWeight: activeTab === tab.id ? 700 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content — lazy placeholder */}
      <div style={{ minHeight: '400px', background: '#16213e', borderRadius: '8px', padding: '16px' }}>
        <p style={{ color: '#888', fontSize: '13px' }}>
          Tab: <strong style={{ color: '#E9C46A' }}>{activeTab}</strong>
          {' '}— component coming in Task 3/4
        </p>
      </div>
    </div>
  )
}
