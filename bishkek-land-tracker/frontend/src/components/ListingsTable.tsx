import { useState } from 'react'
import type { Listing } from '../types'

type SortKey = 'current_price_usd' | 'price_per_sotka' | 'area_sotka' | 'last_seen'

interface Props {
  listings: Listing[]
}

export function ListingsTable({ listings }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('last_seen')
  const [asc, setAsc] = useState(false)

  const sorted = [...listings].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    if (typeof av === 'string' && typeof bv === 'string') return asc ? av.localeCompare(bv) : bv.localeCompare(av)
    return asc ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setAsc(a => !a)
    else { setSortKey(key); setAsc(false) }
  }

  const Th = ({ label, k }: { label: string; k: SortKey }) => (
    <th className="px-3 py-2 text-left text-xs text-gray-500 cursor-pointer select-none hover:text-gray-300"
      onClick={() => toggleSort(k)}>
      {label} {sortKey === k ? (asc ? '↑' : '↓') : ''}
    </th>
  )

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-gray-800">
            <th className="px-3 py-2 text-left text-xs text-gray-500">Район</th>
            <Th label="Площадь" k="area_sotka" />
            <Th label="Цена" k="current_price_usd" />
            <Th label="$/сотка" k="price_per_sotka" />
            <th className="px-3 py-2 text-left text-xs text-gray-500">Изменение</th>
            <th className="px-3 py-2 text-left text-xs text-gray-500">Источник</th>
            <Th label="Дата" k="last_seen" />
          </tr>
        </thead>
        <tbody>
          {sorted.map(l => (
            <tr key={l.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
              onClick={() => window.open(l.url, '_blank')}>
              <td className="px-3 py-2 text-gray-300">{l.district_name}</td>
              <td className="px-3 py-2 text-gray-300">{l.area_sotka} сот.</td>
              <td className="px-3 py-2 font-semibold text-white">${l.current_price_usd.toLocaleString()}</td>
              <td className="px-3 py-2 text-gray-300">${Math.round(l.price_per_sotka).toLocaleString()}</td>
              <td className="px-3 py-2">
                {l.change_pct_today === null || l.change_pct_today === 0
                  ? <span className="text-gray-500">—</span>
                  : l.change_pct_today < 0
                    ? <span className="text-red-400">↓ {l.change_pct_today.toFixed(1)}%</span>
                    : <span className="text-green-400">↑ +{l.change_pct_today.toFixed(1)}%</span>
                }
              </td>
              <td className="px-3 py-2 text-blue-400">{l.source}</td>
              <td className="px-3 py-2 text-gray-500">{l.last_seen}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {listings.length === 0 && (
        <div className="text-center py-8 text-gray-600 text-sm">Нет объявлений</div>
      )}
    </div>
  )
}
