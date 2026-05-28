const PAGES = [
  { id: 'dashboard', label: '📊 Дашборд' },
  { id: 'listings', label: '📋 Объявления' },
  { id: 'trends', label: '📈 Тренды' },
  { id: 'recommendations', label: '⭐ Рекомендации' },
]

interface NavProps { active: string; onNavigate: (page: string) => void }

export function Nav({ active, onNavigate }: NavProps) {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
      <div className="flex gap-4">
        {PAGES.map(p => (
          <button key={p.id} onClick={() => onNavigate(p.id)}
            className={`text-sm transition-colors ${
              active === p.id ? 'text-blue-400 border-b-2 border-blue-400 pb-0.5' : 'text-gray-500 hover:text-gray-300'
            }`}>
            {p.label}
          </button>
        ))}
      </div>
      <div className="text-xs text-gray-600">Bishkek Land Tracker</div>
    </nav>
  )
}
