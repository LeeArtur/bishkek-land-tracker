import type { District, Listing, PriceHistoryEntry, TrendPoint, Deal, MacroData, Filters } from '../types'

// In production VITE_API_URL points to Render backend (e.g. https://bishkek-land-tracker-api.onrender.com)
// In dev, /api is proxied to localhost:8000 by Vite
const BASE = import.meta.env.VITE_API_URL ?? '/api'

async function get<T>(path: string, params?: Record<string, string | number | boolean | null | undefined>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined) url.searchParams.set(k, String(v))
    })
  }
  const fullUrl = BASE.startsWith('http') ? BASE + path + url.search : url.pathname + url.search
  const res = await fetch(fullUrl)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  getDistricts: () => get<District[]>('/districts'),

  getListings: (filters: Partial<Filters>) =>
    get<Listing[]>('/listings', {
      district_id: filters.district_ids?.length === 1 ? filters.district_ids[0] : undefined,
      source: filters.sources?.length === 1 ? filters.sources[0] : undefined,
      min_price: filters.min_price ?? undefined,
      max_price: filters.max_price ?? undefined,
      min_area: filters.min_area ?? undefined,
      max_area: filters.max_area ?? undefined,
      price_changed_today: filters.price_changed_today || undefined,
    }),

  getListingHistory: (id: number) =>
    get<PriceHistoryEntry[]>(`/listings/${id}/history`),

  getTrends: (days: number = 30) =>
    get<TrendPoint[]>('/trends', { days }),

  getRecommendations: () => get<Deal[]>('/recommendations'),

  getMacro: () => get<MacroData | null>('/macro'),

  triggerScrape: () =>
    fetch((import.meta.env.VITE_API_URL ?? '/api') + '/scrape', { method: 'POST' }).then(r => r.json()),
}
