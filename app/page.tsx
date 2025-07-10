'use client'

import ChatInterface from '@/frontend/components/Chat'
import IngestForm from '@/frontend/components/IngestForm'

export default function Home() {
  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Minimalist Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-center">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-2xl">🧠</span>
              </div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
                MyBrain
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Side by Side Layout */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-6 py-6">
          <div className="h-full grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Side - Add Knowledge */}
            <div className="h-full overflow-auto">
              <IngestForm />
            </div>
            
            {/* Right Side - Chat */}
            <div className="h-full overflow-hidden">
              <ChatInterface />
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}