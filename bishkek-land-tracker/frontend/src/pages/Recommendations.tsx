import { useEffect, useState, useMemo } from 'react'
import { api } from '../api/client'
import type { Deal } from '../types'

type SortKey = 'last_seen' | 'discount_pct'

function DealCard({ deal }: { deal: Deal }) {
  return (
    <a
      href={deal.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-gray-900 rounded-xl p-4 border border-gray-800 hover:border-green-500 transition-colors group"
    >
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full font-medium">
          -{deal.discount_pct.toFixed(1)}%
        </span>
        <span className="text-xs text-gray-600">{deal.source}</span>
      </div>

      <div className="mb-3">
        <div className="text-white font-semibold text-lg leading-tight">
          ${deal.current_price_usd.toLocaleString()}
        </div>
        <div className="text-gray-400 text-sm mt-0.5">
          {deal.area_sotka} сот. · ${Math.round(deal.price_per_sotka).toLocaleString()}/сотка
        </div>
      </div>

      <div className="border-t border-gray-800 pt-3">
        <div className="text-xs text-gray-400">{deal.district_name}</div>
        <div className="text-xs text-gray-600 mt-1">
          медиана района: ${Math.round(deal.median_price_per_sotka).toLocaleString()}/сотка
        </div>
      </div>

      <div className="text-xs text-gray-700 mt-2">{deal.last_seen}</div>

      <div className="mt-2 text-xs text-green-500 opacity-0 group-hover:opacity-100 transition-opacity">
        Открыть объявление →
      </div>
    </a>
  )
}

export function Recommendations() {
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('last_seen')

  useEffect(() => {
    api.getRecommendations().then(d => { setDeals(d); setLoading(false) })
  }, [])

  const sorted = useMemo(() => {
    return [...deals].sort((a, b) => {
      if (sortKey === 'discount_pct') return b.discount_pct - a.discount_pct
      return b.last_seen.localeCompare(a.last_seen)
    })
  }, [deals, sortKey])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <div className="text-sm text-gray-400">
          Участки с красной книгой, цена/сотка на 15%+ ниже медианы района
        </div>
        <div className="flex items-center gap-3">
          {!loading && <div className="text-xs text-gray-600">{deals.length} объявлений</div>}
          <div className="flex gap-1">
            <button
              onClick={() => setSortKey('last_seen')}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                sortKey === 'last_seen' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-300'
              }`}
            >
              Новые
            </button>
            <button
              onClick={() => setSortKey('discount_pct')}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                sortKey === 'discount_pct' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-gray-300'
              }`}
            >
              Выгодные
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-44 bg-gray-900 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : deals.length === 0 ? (
        <div className="text-center py-16 text-gray-600">Нет данных</div>
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {sorted.map(deal => <DealCard key={deal.id} deal={deal} />)}
        </div>
      )}
    </div>
  )
}
