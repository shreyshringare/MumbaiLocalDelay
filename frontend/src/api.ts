// Base URL: in dev, Vite proxy forwards /api → localhost:8000
// In prod, api/static/ is served by FastAPI, same origin
const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  const contentType = res.headers.get('content-type')
  if (!contentType?.includes('application/json')) {
    throw new Error(`Expected JSON, got ${contentType ?? 'unknown'}`)
  }
  return res.json() as T
}

// --- Types matching api/schemas.py ---

export interface StationDelay {
  station_name: string
  line: string
  avg_delay: number
  latitude: number | null
  longitude: number | null
}

export interface HeatmapResponse {
  station: string
  matrix: (number | null)[][]
}

export interface RankingEntry {
  station_name: string
  line: string
  avg_delay: number
  ci_lower: number | null
  ci_upper: number | null
}

export interface AnomalyEntry {
  station: string
  severity: string
  actual: number
  expected: number
  upper: number
  date: string
}

export interface LineTrendPoint {
  date: string
  line: string
  avg_delay: number
}

export interface QualityEntry {
  station_name: string
  row_count: number
  unique_dates: number
  last_updated: string | null
}

export interface InsightsResponse {
  worst_station: string
  worst_delay: number
  best_line: string
  best_line_delay: number
  peak_window: string
  delay_hours_per_day: number
  commuters_affected: number
}

export interface ForecastPoint {
  ds: string
  yhat: number
  yhat_lower: number
  yhat_upper: number
}

export interface CorrelationResponse {
  stations: string[]
  matrix: number[][]
}

export interface WaveStation {
  station_name: string
  line_order: number
  delays: number[]  // length 24, index = hour
}

export interface ForecastStatus {
  fitted: number
  total: number
  ready: boolean
}

// --- API functions ---

export const api = {
  mapData: () => get<StationDelay[]>('/map-data'),
  heatmap: (station: string) => get<HeatmapResponse>(`/heatmap?station=${encodeURIComponent(station)}`),
  rankings: (line: string, period: string) => get<RankingEntry[]>(`/rankings?line=${encodeURIComponent(line)}&period=${encodeURIComponent(period)}`),
  anomalies: () => get<AnomalyEntry[]>('/anomalies'),
  lineTrend: (line: string) => get<LineTrendPoint[]>(`/line-trend?line=${encodeURIComponent(line)}`),
  quality: () => get<QualityEntry[]>('/quality'),
  insights: () => get<InsightsResponse>('/insights'),
  forecast: (station: string) => get<ForecastPoint[] | { status: string }>(`/forecast?station=${encodeURIComponent(station)}`),
  correlation: (line: string) => get<CorrelationResponse>(`/correlation?line=${encodeURIComponent(line)}`),
  methodology: () => get<Record<string, unknown>>('/methodology'),
  waveData: (line: string) => get<WaveStation[]>(`/wave-data?line=${encodeURIComponent(line)}`),
  forecastStatus: () => get<ForecastStatus>('/forecast/status'),
}
