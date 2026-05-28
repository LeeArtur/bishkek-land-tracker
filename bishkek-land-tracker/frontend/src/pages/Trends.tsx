import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { District } from '../types'
import { TrendChart } from '../components/TrendChart'

export function Trends() {
  const [districts, setDistricts] = useState<District[]>([])
  useEffect(() => { api.getDistricts().then(setDistricts) }, [])

  return (
    <div className="space-y-4">
      <TrendChart />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {districts.filter(d => d.listing_count > 0).map(d => (
          <div key={d.id} className="bg-gray-900 rounded-xl p-4">
            <div className="text-sm font-medium text-white mb-2">{d.name}</div>
            <div className="text-xs text-gray-400">Медиана: <span className="text-white">${d.median_price_per_sotka?.toLocaleString() ?? '—'}/сотка</span></div>
            <div className="text-xs text-gray-400">Среднее: <span className="text-white">${d.avg_price_per_sotka?.toLocaleString() ?? '—'}/сотка</span></div>
            <div className="text-xs text-gray-500 mt-1">{d.listing_count} объявлений</div>
          </div>
        ))}
      </div>
    </div>
  )
}
