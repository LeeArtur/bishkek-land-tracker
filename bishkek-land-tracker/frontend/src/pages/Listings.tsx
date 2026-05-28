import { useEffect, useState } from 'react'
import { Filters } from '../components/Filters'
import { ListingsTable } from '../components/ListingsTable'
import { useFilters } from '../context/FilterContext'
import { api } from '../api/client'
import type { Listing } from '../types'

export function Listings() {
  const { filters } = useFilters()
  const [listings, setListings] = useState<Listing[]>([])

  useEffect(() => {
    api.getListings(filters).then(setListings)
  }, [filters])

  return (
    <div className="space-y-4">
      <Filters />
      <div className="text-xs text-gray-500">{listings.length} объявлений</div>
      <div className="bg-gray-900 rounded-xl p-4">
        <ListingsTable listings={listings} />
      </div>
    </div>
  )
}
