import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const query = searchParams.get('q')
  
  if (!query) {
    return NextResponse.json(
      { error: 'Query parameter required' },
      { status: 400 }
    )
  }

  try {
    // Call backend quick search
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/search/quick/${encodeURIComponent(query)}`,
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
    
    // Format for Siri
    return NextResponse.json({
      query: data.query,
      answer: data.answer,
      confidence: data.confidence,
      source: data.source?.title || 'MyBrain Knowledge Base',
      additionalInfo: data.additional_results > 0 
        ? `${data.additional_results} weitere Ergebnisse verfügbar`
        : null
    })
  } catch (error) {
    console.error('Quick search error:', error)
    return NextResponse.json(
      { 
        error: 'Search failed',
        answer: 'Es tut mir leid, ich konnte keine Antwort finden.'
      },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const { content, source = 'siri' } = await request.json()
    
    if (!content) {
      return NextResponse.json(
        { error: 'Content required' },
        { status: 400 }
      )
    }

    // Quick capture via backend
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/ingest/quick`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, source })
      }
    )

    if (!response.ok) {
      throw new Error('Backend capture failed')
    }

    const data = await response.json()
    
    return NextResponse.json({
      success: true,
      message: 'Notiz gespeichert',
      documentId: data.document_id
    })
  } catch (error) {
    console.error('Quick capture error:', error)
    return NextResponse.json(
      { 
        error: 'Capture failed',
        message: 'Notiz konnte nicht gespeichert werden'
      },
      { status: 500 }
    )
  }
}