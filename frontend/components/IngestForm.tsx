'use client'

import { useState } from 'react'
import { AlertCircle, CheckCircle, FileText } from 'lucide-react'

export default function IngestForm() {
  const [textTitle, setTextTitle] = useState('')
  const [textContent, setTextContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!textTitle.trim() || !textContent.trim()) return
    
    setIsLoading(true)
    setMessage(null)
    
    try {
      const response = await fetch('/api/backend/ingest/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: textTitle,
          content: textContent,
          source_type: 'text'
        })
      })
      
      if (!response.ok) throw new Error('Failed to ingest text')
      
      const data = await response.json()
      setMessage({ type: 'success', text: `"${textTitle}" wurde erfolgreich gespeichert!` })
      setTextTitle('')
      setTextContent('')
      
      // Clear success message after 5 seconds
      setTimeout(() => setMessage(null), 5000)
    } catch (error) {
      setMessage({ type: 'error', text: 'Fehler beim Speichern des Textes' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
      <div className="mb-6 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full mb-4">
          <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Wissen hinzufügen
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Kopiere einen Text und speichere ihn in deinem persönlichen Wissensspeicher
        </p>
      </div>

      {/* Message Display */}
      {message && (
        <div className={`rounded-lg p-4 mb-6 flex items-center space-x-3 transition-all ${
          message.type === 'success' 
            ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200' 
            : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Simple Text Input Form */}
      <form onSubmit={handleTextSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Titel
          </label>
          <input
            type="text"
            value={textTitle}
            onChange={(e) => setTextTitle(e.target.value)}
            placeholder="z.B. Meeting Notes, Artikel, Idee..."
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white transition-all"
            required
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Text
          </label>
          <textarea
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            placeholder="Füge hier deinen Text ein..."
            rows={12}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white resize-none transition-all"
            required
          />
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {textContent.length} Zeichen
          </p>
        </div>
        
        <button
          type="submit"
          disabled={isLoading || !textTitle.trim() || !textContent.trim()}
          className="w-full px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium text-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
        >
          {isLoading ? 'Wird gespeichert...' : 'Speichern'}
        </button>
      </form>
    </div>
  )
}