import { useState } from 'react'
import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { DashboardTab } from './components/tabs/DashboardTab'
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
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'map', label: 'Station Map' },
  { id: 'heatmap', label: 'Heatmap' },
  { id: 'rankings', label: 'Rankings' },
  { id: 'anomaly', label: 'Anomaly Alerts' },
  { id: 'lines', label: 'Line Comparison' },
  { id: 'prediction', label: 'Prediction' },
  { id: 'correlation', label: 'Correlation' },
  { id: 'quality', label: 'Data Quality' },
  { id: 'insights', label: 'Business Insights' },
  { id: 'methodology', label: 'Methodology' },
  { id: 'ask', label: 'Ask AI' },
] as const

type TabId = (typeof TABS)[number]['id']

function renderTab(tab: TabId): ReactNode {
  switch (tab) {
    case 'dashboard': return <DashboardTab />
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
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '16px' }}>
      <div style={{ marginBottom: '16px' }}>
        <h1 style={{ color: '#E9C46A', fontSize: '22px', fontWeight: 700 }}>
          Mumbai Local Train Delay Visualizer
        </h1>
        <p style={{ color: '#888', fontSize: '13px', marginTop: '4px' }}>
          Prophet forecast · DuckDB analytics · 120+ stations · Central, Western, Harbour
        </p>
      </div>

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

      <div style={{ minHeight: '400px', background: '#16213e', borderRadius: '8px', padding: '16px' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
          >
            {renderTab(activeTab)}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
