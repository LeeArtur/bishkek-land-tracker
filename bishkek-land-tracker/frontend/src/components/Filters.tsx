import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useFilters } from '../context/FilterContext'
import type { District } from '../types'

const SOURCES = ['house.kg', 'lalafo.kg', 'stroka.kg', 'stroika.kg']

export function Filters() {
  const { filters, setFilters, resetFilters } = useFilters()
  const [districts, setDistricts] = useState<District[]>([])

  useEffect(() => { api.getDistricts().then(setDistricts) }, [])

  const toggleSource = (s: string) => {
    const next = filters.sources.includes(s)
      ? filters.sources.filter(x => x !== s)
      : [...filters.sources, s]
    setFilters({ sources: next })
  }

  return (
    <div className="flex gap-3 flex-wrap items-center text-sm">
      <select
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 text-xs"
        value={filters.district_ids[0] ?? ''}
        onChange={e => setFilters({ district_ids: e.target.value ? [Number(e.target.value)] : [] })}>
        <option value="">Все районы</option>
        {districts.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
      </select>

      <div className="flex gap-2 flex-wrap">
        {SOURCES.map(s => (
          <button key={s} onClick={() => toggleSource(s)}
            className={`px-2 py-1 rounded text-xs ${filters.sources.includes(s) ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}>
            {s}
          </button>
        ))}
      </div>

      <input type="number" placeholder="Цена от $" value={filters.min_price ?? ''}
        onChange={e => setFilters({ min_price: e.target.value ? Number(e.target.value) : null })}
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 text-xs w-28" />
      <input type="number" placeholder="Цена до $" value={filters.max_price ?? ''}
        onChange={e => setFilters({ max_price: e.target.value ? Number(e.target.value) : null })}
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 text-xs w-28" />
      <input type="number" placeholder="Соток от" value={filters.min_area ?? ''}
        onChange={e => setFilters({ min_area: e.target.value ? Number(e.target.value) : null })}
        className="bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 text-xs w-24" />

      <label className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
        <input type="checkbox" checked={filters.price_changed_today}
          onChange={e => setFilters({ price_changed_today: e.target.checked })}
          className="accent-blue-500" />
        Цена изменилась сегодня
      </label>

      <button onClick={resetFilters} className="text-xs text-gray-500 hover:text-gray-300 underline">Сбросить</button>
    </div>
  )
}
