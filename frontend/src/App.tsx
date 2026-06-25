import { useState } from 'react'
import type { ReactNode } from 'react'
import { HeatmapTab } from './components/tabs/HeatmapTab'
import { RankingsTab } from './components/tabs/RankingsTab'
import { AnomalyTab } from './components/tabs/AnomalyTab'
import { LineComparisonTab } from './components/tabs/LineComparisonTab'
import { QualityTab } from './components/tabs/QualityTab'
import { InsightsTab } from './components/tabs/InsightsTab'
import { PredictionTab } from './components/tabs/PredictionTab'
import { CorrelationTab } from './components/tabs/CorrelationTab'
import { MethodologyTab } from './components/tabs/MethodologyTab'
import { MapTab } from './components/tabs/MapTab'
import { AskAITab } from './components/tabs/AskAITab'

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
  { id: 'ask', label: 'Ask AI' },
] as const

type TabId = (typeof TABS)[number]['id']

function renderTab(tab: TabId): ReactNode {
  switch (tab) {
    case 'heatmap': return <HeatmapTab />
    case 'rankings': return <RankingsTab />
    case 'anomaly': return <AnomalyTab />
    case 'lines': return <LineComparisonTab />
    case 'quality': return <QualityTab />
    case 'insights': return <InsightsTab />
    case 'prediction': return <PredictionTab />
    case 'correlation': return <CorrelationTab />
    case 'methodology': return <MethodologyTab />
    case 'map': return <MapTab />
    case 'ask': return <AskAITab />
    default: return null
  }
}

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

      {/* Tab content */}
      <div style={{ minHeight: '400px', background: '#16213e', borderRadius: '8px', padding: '16px' }}>
        {renderTab(activeTab)}
      </div>
    </div>
  )
}
