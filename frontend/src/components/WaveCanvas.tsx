import { useRef, useEffect } from 'react'
import type { WaveStation } from '../api'

interface WaveCanvasProps {
  data: WaveStation[]
  width: number
  height: number
  playbackHour: number  // 0–23
  isPlaying: boolean
}

const PL = 120  // PADDING_LEFT  — space for station labels
const PR = 40   // PADDING_RIGHT — space for color legend
const PT = 8    // PADDING_TOP
const PB = 24   // PADDING_BOTTOM — space for hour axis

/** Map delay (0–8+ min) to CSS color green→yellow→red */
function delayColor(delay: number): string {
  const t = Math.min(Math.max(delay, 0) / 8, 1)
  if (t < 0.5) {
    const s = t * 2
    return `rgb(${Math.round(42 + s * 191)},${Math.round(157 + s * 39)},${Math.round(143 - s * 37)})`
  }
  const s = (t - 0.5) * 2
  return `rgb(${Math.round(233 - s * 3)},${Math.round(196 - s * 139)},${Math.round(106 - s * 36)})`
}

export function WaveCanvas({ data, width, height, playbackHour, isPlaying }: WaveCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const hourRef = useRef(playbackHour)
  const rafRef = useRef<number>(0)

  useEffect(() => {
    hourRef.current = playbackHour
  }, [playbackHour])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || data.length === 0) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const stationCount = data.length
    const plotW = width - PL - PR
    const plotH = height - PT - PB
    const rowH = plotH / stationCount

    function xPx(hour: number): number {
      return PL + (hour / 23) * plotW
    }

    function draw() {
      ctx!.clearRect(0, 0, width, height)

      // Draw wave bands
      data.forEach((station, idx) => {
        const yTop = PT + idx * rowH
        for (let px = 0; px < plotW; px++) {
          const hour = Math.floor((px / plotW) * 23)
          ctx!.fillStyle = delayColor(station.delays[hour] ?? 0)
          ctx!.fillRect(PL + px, yTop + 1, 1, rowH - 2)
        }
        // Station label
        ctx!.fillStyle = '#888'
        ctx!.font = '10px monospace'
        ctx!.textAlign = 'right'
        ctx!.fillText(station.station_name, PL - 6, yTop + rowH / 2 + 4)
      })

      // Hour axis
      ctx!.fillStyle = '#444'
      ctx!.textAlign = 'center'
      ctx!.font = '9px monospace'
      ;[0, 6, 12, 18, 23].forEach(h => {
        ctx!.fillText(`${String(h).padStart(2, '0')}:00`, xPx(h), height - 6)
      })

      // Time cursor
      const cursorX = xPx(hourRef.current)
      ctx!.strokeStyle = 'rgba(255,255,255,0.5)'
      ctx!.lineWidth = 1
      ctx!.beginPath()
      ctx!.moveTo(cursorX, PT)
      ctx!.lineTo(cursorX, height - PB)
      ctx!.stroke()
      ctx!.fillStyle = '#fff'
      ctx!.textAlign = 'left'
      ctx!.font = '9px monospace'
      ctx!.fillText(`${String(Math.floor(hourRef.current)).padStart(2, '0')}:00`, cursorX + 3, PT + 10)

      // Color legend
      const gradH = height - PT - PB
      const grad = ctx!.createLinearGradient(width - PR + 4, PT, width - PR + 4, PT + gradH)
      grad.addColorStop(0, delayColor(8))
      grad.addColorStop(0.5, delayColor(4))
      grad.addColorStop(1, delayColor(0))
      ctx!.fillStyle = grad
      ctx!.fillRect(width - PR + 4, PT, 8, gradH)
      ctx!.fillStyle = '#555'
      ctx!.font = '9px monospace'
      ctx!.textAlign = 'left'
      ctx!.fillText('8m', width - PR + 14, PT + 10)
      ctx!.fillText('0', width - PR + 14, PT + gradH)

      if (isPlaying) {
        hourRef.current = (hourRef.current + 0.015) % 24
        rafRef.current = requestAnimationFrame(draw)
      }
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [data, width, height, isPlaying])

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ display: 'block', width: '100%', height: `${height}px` }}
    />
  )
}
