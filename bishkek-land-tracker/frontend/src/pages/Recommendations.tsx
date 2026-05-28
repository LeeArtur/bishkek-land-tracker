import { DealsPanel } from '../components/DealsPanel'

export function Recommendations() {
  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-400">
        Объявления с ценой за сотку на 15%+ ниже медианной по своему району.
      </div>
      <DealsPanel limit={100} />
    </div>
  )
}
