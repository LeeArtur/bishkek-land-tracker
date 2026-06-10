const PAGES = [
  { id: 'dashboard', label: '📊', fullLabel: 'Дашборд' },
  { id: 'listings', label: '📋', fullLabel: 'Объявления' },
  { id: 'trends', label: '📈', fullLabel: 'Тренды' },
  { id: 'recommendations', label: '⭐', fullLabel: 'Рекомендации' },
]

interface NavProps { active: string; onNavigate: (page: string) => void }

export function Nav({ active, onNavigate }: NavProps) {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-3 py-2 flex items-center justify-between">
      <div className="flex gap-1 sm:gap-4 overflow-x-auto">
        {PAGES.map(p => (
          <button key={p.id} onClick={() => onNavigate(p.id)}
            className={`whitespace-nowrap px-2 py-1.5 rounded text-sm transition-colors flex-shrink-0 ${
              active === p.id
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-500 hover:text-gray-300'
            }`}>
            <span className="sm:hidden">{p.label}</span>
            <span className="hidden sm:inline">{p.label} {p.fullLabel}</span>
          </button>
        ))}
      </div>
      <div className="text-xs text-gray-600 hidden sm:block flex-shrink-0 ml-2">Bishkek Land Tracker</div>
    </nav>
  )
}
