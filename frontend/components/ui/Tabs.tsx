'use client'

import * as React from 'react'

interface TabsProps {
  value: string
  onValueChange: (value: string) => void
  className?: string
  children: React.ReactNode
}

export function Tabs({ value, onValueChange, className, children }: TabsProps) {
  return (
    <div className={className} data-value={value}>
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { value, onValueChange } as any)
        }
        return child
      })}
    </div>
  )
}

interface TabsListProps {
  className?: string
  children: React.ReactNode
  value?: string
  onValueChange?: (value: string) => void
}

export function TabsList({ className, children, value, onValueChange }: TabsListProps) {
  return (
    <div className={`inline-flex h-10 items-center justify-center rounded-md bg-gray-100 dark:bg-gray-800 p-1 ${className || ''}`}>
      {React.Children.map(children, child => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child, { value, onValueChange } as any)
        }
        return child
      })}
    </div>
  )
}

interface TabsTriggerProps {
  value: string
  className?: string
  children: React.ReactNode
  currentValue?: string
  onValueChange?: (value: string) => void
}

export function TabsTrigger({ value: triggerValue, className, children, value: currentValue, onValueChange }: TabsTriggerProps) {
  const isActive = currentValue === triggerValue
  
  return (
    <button
      className={`
        inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 
        text-sm font-medium ring-offset-white transition-all 
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-950 
        focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50
        ${isActive 
          ? 'bg-white dark:bg-gray-900 text-gray-950 dark:text-gray-50 shadow-sm' 
          : 'text-gray-700 dark:text-gray-400 hover:text-gray-950 dark:hover:text-gray-50'
        }
        ${className || ''}
      `}
      onClick={() => onValueChange?.(triggerValue)}
    >
      {children}
    </button>
  )
}

interface TabsContentProps {
  value: string
  className?: string
  children: React.ReactNode
  currentValue?: string
}

export function TabsContent({ value: contentValue, className, children, value: currentValue }: TabsContentProps) {
  if (currentValue !== contentValue) return null
  
  return (
    <div
      className={`mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-950 focus-visible:ring-offset-2 ${className || ''}`}
    >
      {children}
    </div>
  )
}