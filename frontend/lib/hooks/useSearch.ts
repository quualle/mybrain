'use client'

import { useState, useCallback } from 'react'
import type { SearchResult } from '../types'

export function useSearch() {
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(async (
    query: string,
    filters?: {
      speaker?: string
      startDate?: Date
      endDate?: Date
      sourceType?: string
    }
  ) => {
    setIsSearching(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        q: query,
        limit: '20',
        use_colbert: 'true'
      })

      if (filters?.speaker) params.append('speaker', filters.speaker)
      if (filters?.sourceType) params.append('source_type', filters.sourceType)
      if (filters?.startDate) params.append('start_date', filters.startDate.toISOString())
      if (filters?.endDate) params.append('end_date', filters.endDate.toISOString())

      const response = await fetch(`/api/backend/search?${params}`)
      
      if (!response.ok) throw new Error('Search failed')
      
      const data = await response.json()
      setResults(data.results)
      
      return data.results
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search error')
      return []
    } finally {
      setIsSearching(false)
    }
  }, [])

  const searchBySpeaker = useCallback(async (speaker: string, query?: string) => {
    setIsSearching(true)
    setError(null)

    try {
      const params = new URLSearchParams({ limit: '20' })
      if (query) params.append('q', query)

      const response = await fetch(`/api/backend/search/speaker/${encodeURIComponent(speaker)}?${params}`)
      
      if (!response.ok) throw new Error('Speaker search failed')
      
      const data = await response.json()
      setResults(data.results)
      
      return data.results
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search error')
      return []
    } finally {
      setIsSearching(false)
    }
  }, [])

  const searchToday = useCallback(async (query?: string) => {
    setIsSearching(true)
    setError(null)

    try {
      const params = new URLSearchParams()
      if (query) params.append('q', query)

      const response = await fetch(`/api/backend/search/today?${params}`)
      
      if (!response.ok) throw new Error('Today search failed')
      
      const data = await response.json()
      setResults(data.results)
      
      return data.results
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search error')
      return []
    } finally {
      setIsSearching(false)
    }
  }, [])

  const clearResults = useCallback(() => {
    setResults(null)
    setError(null)
  }, [])

  return {
    results,
    isSearching,
    error,
    search,
    searchBySpeaker,
    searchToday,
    clearResults
  }
}