import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Deal } from '../types'

export function DealsPanel({ limit = 3 }: { limit?: number }) {
  const [deals, setDeals] = useState<Deal[]>([])

  useEffect(() => { api.getRecommendations().then(setDeals) }, [])

  if (deals.length === 0) return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="text-sm text-gray-400 mb-2">Выгодные сделки</div>
      <div className="text-gray-600 text-sm">Нет данных</div>
    </div>
  )

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="text-sm text-gray-400 mb-1">Выгодные сделки</div>
      <div className="text-xs text-gray-600 mb-3">Ниже медианы района на 15%+</div>
      <div className="flex flex-col gap-2">
        {deals.slice(0, limit).map(deal => (
          <a key={deal.id} href={deal.url} target="_blank" rel="noopener noreferrer"
            className="block bg-gray-800 rounded-lg p-3 border-l-2 border-green-400 hover:bg-gray-750 transition-colors">
            <div className="text-xs text-white mb-1">{deal.district_name}, {deal.area_sotka} сот.</div>
            <div className="text-lg font-bold text-green-400">${deal.current_price_usd.toLocaleString()}</div>
            <div className="text-xs text-gray-500">${Math.round(deal.price_per_sotka).toLocaleString()}/сотка · медиана ${Math.round(deal.median_price_per_sotka).toLocaleString()}</div>
            <div className="text-xs text-green-400 mt-1">-{deal.discount_pct.toFixed(1)}% · {deal.source}</div>
          </a>
        ))}
      </div>
    </div>
  )
}
