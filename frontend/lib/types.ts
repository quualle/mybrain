export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  model?: string
  sources?: Source[]
}

export interface Source {
  title: string
  type: 'youtube' | 'audio' | 'text'
  date?: string
  speaker?: string
  score?: number
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  content: string
  chunk_index: number
  similarity: number
  rank?: number
  metadata?: Record<string, any>
  speaker?: string
  start_time?: number
  end_time?: number
  document?: {
    title: string
    source_type: string
    created_at: string
  }
}

export interface Document {
  id: string
  title: string
  source_type: 'youtube' | 'audio' | 'text' | 'pdf'
  source_url?: string
  duration_seconds?: number
  created_at: string
  summary?: string
  metadata?: Record<string, any>
}