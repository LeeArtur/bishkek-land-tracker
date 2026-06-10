export interface District {
  id: number
  name: string
  avg_price_per_sotka: number | null
  median_price_per_sotka: number | null
  listing_count: number
}

export interface Listing {
  id: number
  external_id: string
  source: string
  title: string
  district_id: number
  district_name: string
  area_sotka: number
  current_price_usd: number
  price_per_sotka: number
  url: string
  first_seen: string
  last_seen: string
  is_active: boolean
  price_changed_today: boolean
  change_pct_today: number | null
}

export interface PriceHistoryEntry {
  price_usd: number
  price_per_sotka: number
  recorded_at: string
  change_pct: number | null
}

export interface TrendPoint {
  date: string
  district_id: number
  district_name: string
  median_price_per_sotka: number
  sample_count: number
}

export interface Deal extends Listing {
  median_price_per_sotka: number
  discount_pct: number
  published_at: string | null
}

export interface MacroData {
  recorded_at: string
  usd_kgs_rate: number
  source: string
}

export interface Filters {
  district_ids: number[]
  sources: string[]
  min_price: number | null
  max_price: number | null
  min_area: number | null
  max_area: number | null
  price_changed_today: boolean
}
