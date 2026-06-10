import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Listing, Deal } from '../types'

interface Stats {
  totalListings: number
  avgPricePerSotka: number
  priceDropsToday: number
  dealsCount: number
}

function StatCard({ label, value, sub, accent }: {
  label: string; value: string; sub: string; accent: string
}) {
  return (
    <div className={`bg-gray-900 rounded-xl p-4 border-l-4 ${accent} flex-1 min-w-[140px]`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{sub}</div>
    </div>
  )
}

export function SummaryCards() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    Promise.all([
      api.getListings({}),
      api.getListings({ price_changed_today: true }),
      api.getRecommendations(),
    ]).then(([all, changed, deals]: [Listing[], Listing[], Deal[]]) => {
      const prices = all.map(l => l.price_per_sotka).filter(p => p > 0)
      const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0
      setStats({
        totalListings: all.length,
        avgPricePerSotka: Math.round(avg),
        priceDropsToday: changed.filter(l => (l.change_pct_today ?? 0) < 0).length,
        dealsCount: deals.length,
      })
    })
  }, [])

  if (!stats) return (
    <div className="grid grid-cols-2 sm:flex gap-3 flex-wrap">
      {[1,2,3,4].map(i => <div key={i} className="flex-1 h-20 bg-gray-800 rounded-xl animate-pulse min-w-[140px]" />)}
    </div>
  )

  return (
    <div className="grid grid-cols-2 sm:flex gap-3 flex-wrap">
      <StatCard label="Всего объявлений" value={stats.totalListings.toLocaleString()} sub="активных" accent="border-blue-500" />
      <StatCard label="Средняя цена / сотка" value={`$${stats.avgPricePerSotka.toLocaleString()}`} sub="по всем районам" accent="border-yellow-400" />
      <StatCard label="Снижение цен сегодня" value={String(stats.priceDropsToday)} sub="объявлений снизили цену" accent="border-green-400" />
      <StatCard label="Выгодных сделок" value={String(stats.dealsCount)} sub="ниже среднего на 15%+" accent="border-purple-400" />
    </div>
  )
}
