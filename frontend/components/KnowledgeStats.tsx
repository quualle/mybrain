'use client'

import { useEffect, useState } from 'react'
import { FileText, Clock, Users, Database } from 'lucide-react'

interface Stats {
  totalDocuments: number
  totalHours: number
  totalSpeakers: number
  storageUsed: string
}

export default function KnowledgeStats() {
  const [stats, setStats] = useState<Stats>({
    totalDocuments: 0,
    totalHours: 0,
    totalSpeakers: 0,
    storageUsed: '0 MB'
  })

  useEffect(() => {
    // TODO: Fetch real stats from API
    // For now, using placeholder data
    setStats({
      totalDocuments: 42,
      totalHours: 67.5,
      totalSpeakers: 12,
      storageUsed: '234 MB'
    })
  }, [])

  return (
    <div className="flex items-center space-x-6 text-sm">
      <div className="flex items-center space-x-2 text-gray-600 dark:text-gray-400">
        <FileText className="w-4 h-4" />
        <span>{stats.totalDocuments} Dokumente</span>
      </div>
      <div className="flex items-center space-x-2 text-gray-600 dark:text-gray-400">
        <Clock className="w-4 h-4" />
        <span>{stats.totalHours.toFixed(1)} Stunden</span>
      </div>
      <div className="flex items-center space-x-2 text-gray-600 dark:text-gray-400">
        <Users className="w-4 h-4" />
        <span>{stats.totalSpeakers} Personen</span>
      </div>
      <div className="flex items-center space-x-2 text-gray-600 dark:text-gray-400">
        <Database className="w-4 h-4" />
        <span>{stats.storageUsed}</span>
      </div>
    </div>
  )
}