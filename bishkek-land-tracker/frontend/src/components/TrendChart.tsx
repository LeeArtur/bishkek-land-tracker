import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import type { TrendPoint } from '../types'

const COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#fb923c']

type Period = 30 | 90 | 365

interface ChartRow {
  date: string
  [key: string]: number | string
}

export function TrendChart() {
  const [period, setPeriod] = useState<Period>(30)
  const [rows, setRows] = useState<ChartRow[]>([])
  const [districts, setDistricts] = useState<string[]>([])

  useEffect(() => {
    api.getTrends(period).then((points: TrendPoint[]) => {
      // Count samples per district, keep top 5
      const sampleCount: Record<string, number> = {}
      points.forEach(p => { sampleCount[p.district_name] = (sampleCount[p.district_name] ?? 0) + p.sample_count })
      const top5 = Object.entries(sampleCount)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([name]) => name)
      const top5Set = new Set(top5)

      const byDate: Record<string, ChartRow> = {}
      points.forEach(p => {
        if (!top5Set.has(p.district_name)) return
        if (!byDate[p.date]) byDate[p.date] = { date: p.date }
        byDate[p.date][p.district_name] = p.median_price_per_sotka
      })
      setRows(Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date)))
      setDistricts(top5)
    })
  }, [period])

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-gray-400">Тренд медианной цены / сотка по районам</span>
        <div className="flex gap-2">
          {([30, 90, 365] as Period[]).map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded text-xs ${period === p ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>
              {p === 365 ? '1 год' : `${p}д`}
            </button>
          ))}
        </div>
      </div>
      {rows.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-gray-600 text-sm">Нет данных</div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d3d" />
            <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 11 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={v => `$${v}`} />
            <Tooltip formatter={(v) => [`$${Number(v).toLocaleString()}`, '']} contentStyle={{ background: '#111827', border: '1px solid #1e2d3d' }} />
            <Legend />
            {districts.map((d, i) => (
              <Line key={d} type="monotone" dataKey={d} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
