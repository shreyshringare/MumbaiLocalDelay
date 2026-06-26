import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { WaveCanvas } from '../WaveCanvas'
import { LoadingSpinner } from '../LoadingSpinner'
import { ErrorMessage } from '../ErrorMessage'

type Line = 'Central' | 'Western' | 'Harbour'

export function DashboardTab() {
  const [line, setLine] = useState<Line>('Central')
  const [playbackHour, setPlaybackHour] = useState(8)
  const [isPlaying, setIsPlaying] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const [canvasWidth, setCanvasWidth] = useState(800)

  const { data, isLoading, error } = useQuery({
    queryKey: ['wave-data', line],
    queryFn: () => api.waveData(line),
    staleTime: 5 * 60 * 1000,
  })

  const { data: insights } = useQuery({
    queryKey: ['insights'],
    queryFn: api.insights,
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    const ro = new ResizeObserver(([entry]) => {
      setCanvasWidth(entry.contentRect.width)
    })
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  return (
    <div>
      {/* Title row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
        <span style={{ color: '#E9C46A', fontSize: '15px', fontWeight: 700 }}>
          Delay Propagation — {line} Line
        </span>
        <select
          value={line}
          onChange={e => setLine(e.target.value as Line)}
          style={{ background: '#2a2a3e', color: '#aaa', border: '1px solid #444', borderRadius: '4px', padding: '2px 8px', fontSize: '11px' }}
        >
          <option>Central</option>
          <option>Western</option>
          <option>Harbour</option>
        </select>
      </div>

      {/* Provenance — always visible */}
      <p style={{ color: '#666', fontSize: '11px', margin: '0 0 12px 0' }}>
        Simulated delays · calibrated on real Indian Railways timetable · not live data
      </p>

      {/* Canvas */}
      <div ref={containerRef} style={{ background: '#0d1b2a', borderRadius: '6px', overflow: 'hidden' }}>
        {isLoading && <LoadingSpinner />}
        {error && <ErrorMessage message={error instanceof Error ? error.message : String(error)} />}
        {data && data.length > 0 && (
          <WaveCanvas
            data={data}
            width={canvasWidth}
            height={300}
            playbackHour={playbackHour}
            isPlaying={isPlaying}
          />
        )}
      </div>

      {/* Time slider */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
        <span style={{ color: '#555', fontSize: '10px' }}>00:00</span>
        <input
          type="range" min={0} max={23} step={0.1}
          value={playbackHour}
          onChange={e => { setIsPlaying(false); setPlaybackHour(Number(e.target.value)) }}
          style={{ flex: 1, accentColor: '#E9C46A' }}
        />
        <span style={{ color: '#555', fontSize: '10px' }}>23:00</span>
        <button
          onClick={() => setIsPlaying(p => !p)}
          style={{ background: '#2a2a3e', border: '1px solid #444', color: '#aaa', padding: '2px 10px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>
      </div>

      {/* KPI chips */}
      {insights && (
        <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
          <KpiChip label="Highest Latency Node" value={insights.worst_station} detail={`${insights.worst_delay.toFixed(1)} min avg latency`} accent="#E63946" />
          <KpiChip label="Best SLA Line" value={insights.best_line} detail={`${insights.best_line_delay.toFixed(1)} min avg latency`} accent="#2a9d8f" />
          <KpiChip label="Pax-hrs Lost/Day" value={insights.delay_hours_per_day.toLocaleString()} detail="est. at ±20% uncertainty" accent="#E9C46A" />
          <KpiChip label="Peak Congestion Window" value={insights.peak_window} detail="Highest latency period" accent="#A8DADC" />
        </div>
      )}
    </div>
  )
}

function KpiChip({ label, value, detail, accent }: { label: string; value: string | number; detail: string; accent: string }) {
  return (
    <div style={{ background: '#1e2a3e', borderRadius: '8px', padding: '10px 14px', minWidth: '160px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{ color: accent, fontSize: '18px', fontWeight: 700 }}>{value}</span>
        <span style={{ color: '#eaeaea', fontSize: '12px' }}>{label}</span>
      </div>
      <p style={{ color: '#666', fontSize: '10px', margin: '3px 0 0 0' }}>{detail}</p>
    </div>
  )
}
