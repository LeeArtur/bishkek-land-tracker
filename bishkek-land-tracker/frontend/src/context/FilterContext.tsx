import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { Filters } from '../types'

const DEFAULT_FILTERS: Filters = {
  district_ids: [],
  sources: [],
  min_price: null,
  max_price: null,
  min_area: null,
  max_area: null,
  price_changed_today: false,
}

interface FilterContextValue {
  filters: Filters
  setFilters: (f: Partial<Filters>) => void
  resetFilters: () => void
}

const FilterContext = createContext<FilterContextValue | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFiltersState] = useState<Filters>(DEFAULT_FILTERS)
  const setFilters = (patch: Partial<Filters>) =>
    setFiltersState(prev => ({ ...prev, ...patch }))
  const resetFilters = () => setFiltersState(DEFAULT_FILTERS)
  return (
    <FilterContext.Provider value={{ filters, setFilters, resetFilters }}>
      {children}
    </FilterContext.Provider>
  )
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useFilters must be used within FilterProvider')
  return ctx
}
