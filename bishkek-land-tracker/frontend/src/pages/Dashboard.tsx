import { useEffect, useState } from 'react'
import { SummaryCards } from '../components/SummaryCards'
import { TrendChart } from '../components/TrendChart'
import { DealsPanel } from '../components/DealsPanel'
import { api } from '../api/client'
import type { MacroData } from '../types'

export function Dashboard() {
  const [macro, setMacro] = useState<MacroData | null>(null)

  useEffect(() => { api.getMacro().then(setMacro) }, [])

  return (
    <div className="space-y-4">
      {macro && (
        <div className="text-xs text-gray-500">
          Курс USD/KGS: {macro.usd_kgs_rate} · обновлено {macro.recorded_at}
        </div>
      )}
      <SummaryCards />
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
