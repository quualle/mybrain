import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Database types (can be generated with Supabase CLI)
export interface Database {
  public: {
    Tables: {
      documents: {
        Row: {
          id: string
          title: string
          source_type: 'youtube' | 'audio' | 'text' | 'pdf' | 'web'
          source_url: string | null
          duration_seconds: number | null
          language: string
          created_at: string
          updated_at: string
          metadata: Record<string, any>
          summary: string | null
          summary_embedding: number[] | null
        }
        Insert: Omit<Database['public']['Tables']['documents']['Row'], 'id' | 'created_at' | 'updated_at'>
        Update: Partial<Database['public']['Tables']['documents']['Insert']>
      }
      chunks: {
        Row: {
          id: string
          document_id: string
          content: string
          chunk_index: number
          chunk_type: 'summary' | 'topic' | 'detail'
          start_time: number | null
          end_time: number | null
          speaker: string | null
          embedding: number[] | null
          created_at: string
          metadata: Record<string, any>
          tokens: number | null
          importance_score: number
        }
        Insert: Omit<Database['public']['Tables']['chunks']['Row'], 'id' | 'created_at'>
        Update: Partial<Database['public']['Tables']['chunks']['Insert']>
      }
    }
  }
}