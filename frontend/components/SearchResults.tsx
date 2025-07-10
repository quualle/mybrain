'use client'

import { FileText, Calendar, User, Clock, ArrowRight } from 'lucide-react'
import type { SearchResult } from '@/frontend/lib/types'

interface SearchResultsProps {
  results: SearchResult[]
  query: string
}

export default function SearchResults({ results, query }: SearchResultsProps) {
  const highlightQuery = (text: string) => {
    const parts = text.split(new RegExp(`(${query})`, 'gi'))
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() 
        ? <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 px-0.5">{part}</mark>
        : part
    )
  }

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-4 mt-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">
          {results.length} Ergebnisse für "{query}"
        </h3>
      </div>

      <div className="space-y-3">
        {results.map((result) => (
          <div
            key={result.chunk_id}
            className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4 text-gray-400" />
                <h4 className="font-medium text-gray-900 dark:text-white">
                  {result.document?.title || 'Unbekanntes Dokument'}
                </h4>
                {result.similarity > 0.8 && (
                  <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 text-xs rounded-full">
                    Hohe Relevanz
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-500">
                {(result.similarity * 100).toFixed(0)}% Match
              </span>
            </div>

            <p className="text-sm text-gray-700 dark:text-gray-300 mb-3 line-clamp-3">
              {highlightQuery(result.content)}
            </p>

            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <div className="flex items-center space-x-4">
                {result.speaker && (
                  <div className="flex items-center space-x-1">
                    <User className="w-3 h-3" />
                    <span>{result.speaker}</span>
                  </div>
                )}
                {result.start_time && (
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{formatTime(result.start_time)}</span>
                  </div>
                )}
                {result.document?.created_at && (
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3 h-3" />
                    <span>
                      {new Date(result.document.created_at).toLocaleDateString('de-DE')}
                    </span>
                  </div>
                )}
              </div>
              <ArrowRight className="w-4 h-4" />
            </div>
          </div>
        ))}
      </div>

      {results.length > 10 && (
        <div className="text-center">
          <button className="text-primary-600 hover:text-primary-700 text-sm font-medium">
            Weitere Ergebnisse anzeigen
          </button>
        </div>
      )}
    </div>
  )
}