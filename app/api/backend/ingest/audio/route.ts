import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    
    const response = await fetch(`${BACKEND_URL}/api/v1/ingest/audio`, {
      method: 'POST',
      body: formData,
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    
    return NextResponse.json(data)
  } catch (error) {
    console.error('Audio ingest error:', error)
    return NextResponse.json(
      { detail: 'Failed to process audio file' },
      { status: 500 }
    )
  }
}