import { useState } from 'react'
import { FilterProvider } from './context/FilterContext'
import { Nav } from './components/Nav'
import { Dashboard } from './pages/Dashboard'
import { Listings } from './pages/Listings'
import { Trends } from './pages/Trends'
import { Recommendations } from './pages/Recommendations'

type Page = 'dashboard' | 'listings' | 'trends' | 'recommendations'

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')

  const content: Record<Page, React.ReactNode> = {
    dashboard: <Dashboard />,
    listings: <Listings />,
    trends: <Trends />,
    recommendations: <Recommendations />,
  }

  return (
    <FilterProvider>
      <div className="min-h-screen bg-gray-950 text-white">
        <Nav active={page} onNavigate={(p) => setPage(p as Page)} />
        <main className="max-w-7xl mx-auto px-4 py-6">
          {content[page]}
        </main>
      </div>
    </FilterProvider>
  )
}
