'use client'

import { useState } from 'react'
import { Search, Filter, Calendar, User, FileType } from 'lucide-react'
import { useSearch } from '@/frontend/lib/hooks/useSearch'
import SearchResults from './SearchResults'

export default function SearchBar() {
  const [query, setQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const { results, isSearching, search } = useSearch()

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      await search(query)
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearch} className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Durchsuche dein Wissen..."
            className="w-full pl-10 pr-20 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
          />
          <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-md transition-colors"
            >
              <Filter className="w-4 h-4 text-gray-500" />
            </button>
            <button
              type="submit"
              disabled={!query.trim() || isSearching}
              className="px-4 py-1.5 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
            >
              Suchen
            </button>
          </div>
        </div>
      </form>

      {showFilters && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="font-medium mb-3">Filter</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Zeitraum</label>
              <div className="flex items-center space-x-2">
                <Calendar className="w-4 h-4 text-gray-400" />
                <select className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700">
                  <option>Alle</option>
                  <option>Heute</option>
                  <option>Diese Woche</option>
                  <option>Diesen Monat</option>
                  <option>Letzten 3 Monate</option>
                </select>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Sprecher</label>
              <div className="flex items-center space-x-2">
                <User className="w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Name..."
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Typ</label>
              <div className="flex items-center space-x-2">
                <FileType className="w-4 h-4 text-gray-400" />
                <select className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700">
                  <option>Alle</option>
                  <option>YouTube</option>
                  <option>Gespräch</option>
                  <option>Notiz</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {results && <SearchResults results={results} query={query} />}
    </div>
  )
}