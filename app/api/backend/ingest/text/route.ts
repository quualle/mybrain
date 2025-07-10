import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    console.log('Forwarding to backend:', `${BACKEND_URL}/api/v1/ingest/text`)
    console.log('Request body:', JSON.stringify(body))
    
    const response = await fetch(`${BACKEND_URL}/api/v1/ingest/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    
    const contentType = response.headers.get('content-type')
    console.log('Response status:', response.status)
    console.log('Response content-type:', contentType)
    
    if (!contentType || !contentType.includes('application/json')) {
      const text = await response.text()
      console.error('Non-JSON response:', text.substring(0, 500))
      return NextResponse.json(
        { detail: 'Backend returned non-JSON response', status: response.status },
        { status: 500 }
      )
    }
    
    const data = await response.json()
    
    if (!response.ok) {
      console.error('Backend error:', data)
      return NextResponse.json(data, { status: response.status })
    }
    
    return NextResponse.json(data)
  } catch (error) {
    console.error('Text ingest error:', error)
    return NextResponse.json(
      { detail: 'Failed to process text' },
      { status: 500 }
    )
  }
}