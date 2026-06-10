import { useEffect, useState } from 'react'
import { SummaryCards } from '../components/SummaryCards'
import { TrendChart } from '../components/TrendChart'
import { DealsPanel } from '../components/DealsPanel'
import { Filters } from '../components/Filters'
import { api } from '../api/client'
import type { MacroData } from '../types'

export function Dashboard() {
  const [macro, setMacro] = useState<MacroData | null>(null)
  const [scraping, setScraping] = useState(false)

  useEffect(() => { api.getMacro().then(setMacro) }, [])

  const handleScrape = () => {
    setScraping(true)
    api.triggerScrape().finally(() => setTimeout(() => setScraping(false), 3000))
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          {macro ? `Курс USD/KGS: ${macro.usd_kgs_rate} · обновлено ${macro.recorded_at}` : ''}
        </div>
        <button onClick={handleScrape} disabled={scraping}
          className="text-xs bg-green-900 hover:bg-green-800 text-green-300 px-3 py-1.5 rounded-lg disabled:opacity-50">
          {scraping ? '⏳ Парсинг...' : '🔄 Обновить данные'}
        </button>
      </div>
      <SummaryCards />
      <Filters />
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="min-w-0 lg:flex-[2]">
          <TrendChart />
        </div>
        <div className="min-w-0 lg:flex-[1]">
          <DealsPanel limit={3} />
        </div>
      </div>
    </div>
  )
}
