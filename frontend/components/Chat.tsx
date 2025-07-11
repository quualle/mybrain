'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquarePlus } from 'lucide-react'
import MessageList from './MessageList'
import { useChat } from '@/frontend/lib/hooks/useChat'

export default function ChatInterface() {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { messages, isLoading, sendMessage, clearMessages } = useChat()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const message = input.trim()
    setInput('')
    await sendMessage(message)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-lg">
      {/* Header with New Chat Button */}
      {messages.length > 0 && (
        <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex justify-end">
          <button
            onClick={clearMessages}
            className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <MessageSquarePlus className="w-4 h-4" />
            <span>Neuen Chat beginnen</span>
          </button>
        </div>
      )}
      
      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList messages={messages} isLoading={isLoading} />
      </div>

      {/* Simplified Input */}
      <form onSubmit={handleSubmit} className="p-6 border-t border-gray-100 dark:border-gray-700">
        <div className="flex items-center space-x-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Frage dein Wissen..."
            rows={1}
            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white transition-all"
            style={{ minHeight: '48px', maxHeight: '120px' }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center space-x-2"
          >
            <Send className="w-5 h-5" />
            <span>Senden</span>
          </button>
        </div>
      </form>
    </div>
  )
}