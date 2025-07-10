import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { name: string } }
) {
  const name = decodeURIComponent(params.name)
  
  try {
    // Search by speaker
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/search/speaker/${encodeURIComponent(name)}?limit=5`,
      {
        headers: {
          'Content-Type': 'application/json',
        }
      }
    )

    if (!response.ok) {
      throw new Error('Backend search failed')
    }

    const data = await response.json()
    
    if (!data.results || data.results.length === 0) {
      return NextResponse.json({
        person: name,
        summary: `Keine Informationen über ${name} gefunden.`,
        lastMeeting: null,
        topics: []
      })
    }

    // Extract key information
    const results = data.results
    const lastMeeting = results[0]
    const topics = extractTopics(results)
    
    // Create summary
    const summary = `${results.length} Einträge gefunden. Letztes Gespräch: ${
      lastMeeting.document?.created_at 
        ? new Date(lastMeeting.document.created_at).toLocaleDateString('de-DE')
        : 'Unbekannt'
    }. Hauptthemen: ${topics.slice(0, 3).join(', ')}.`

    return NextResponse.json({
      person: name,
      summary,
      lastMeeting: {
        date: lastMeeting.document?.created_at,
        content: lastMeeting.content.substring(0, 200) + '...',
        duration: lastMeeting.end_time ? Math.round(lastMeeting.end_time / 60) : null
      },
      topics,
      totalResults: data.total_results
    })
  } catch (error) {
    console.error('Person search error:', error)
    return NextResponse.json(
      { 
        error: 'Search failed',
        person: name,
        summary: 'Es ist ein Fehler aufgetreten.'
      },
      { status: 500 }
    )
  }
}

function extractTopics(results: any[]): string[] {
  // Simple topic extraction - in production, use NLP
  const words: { [key: string]: number } = {}
  const stopWords = new Set(['der', 'die', 'das', 'und', 'oder', 'aber', 'in', 'mit', 'von', 'zu', 'ist', 'sind', 'war', 'waren'])
  
  results.forEach(result => {
    const content = result.content.toLowerCase()
    const tokens = content.split(/\s+/)
    
    tokens.forEach(token => {
      const cleaned = token.replace(/[.,!?;:]/g, '')
      if (cleaned.length > 4 && !stopWords.has(cleaned)) {
        words[cleaned] = (words[cleaned] || 0) + 1
      }
    })
  })
  
  // Sort by frequency and return top words
  return Object.entries(words)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([word]) => word)
}