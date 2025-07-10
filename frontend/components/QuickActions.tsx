'use client'

import { Calendar, Users, Clock, TrendingUp } from 'lucide-react'

export default function QuickActions() {
  const actions = [
    {
      icon: Calendar,
      label: 'Heute',
      description: 'Was war heute wichtig?',
      action: () => console.log('Search today')
    },
    {
      icon: Users,
      label: 'Letzte Meetings',
      description: 'Gespräche der letzten Woche',
      action: () => console.log('Recent meetings')
    },
    {
      icon: Clock,
      label: 'Diese Woche',
      description: 'Zusammenfassung der Woche',
      action: () => console.log('This week')
    },
    {
      icon: TrendingUp,
      label: 'Wichtige Themen',
      description: 'Häufig diskutierte Themen',
      action: () => console.log('Important topics')
    }
  ]

  return (
    <div>
      <h3 className="text-lg font-medium mb-4">Schnellzugriff</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {actions.map((action, idx) => {
          const Icon = action.icon
          return (
            <button
              key={idx}
              onClick={action.action}
              className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all hover:scale-[1.02] text-left"
            >
              <div className="flex items-center space-x-3 mb-2">
                <div className="w-10 h-10 bg-primary-100 dark:bg-primary-900 rounded-lg flex items-center justify-center">
                  <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>
                <h4 className="font-medium">{action.label}</h4>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {action.description}
              </p>
            </button>
          )
        })}
      </div>
    </div>
  )
}