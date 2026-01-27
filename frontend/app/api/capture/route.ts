import { NextRequest, NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    // Get the FormData from the request
    const formData = await request.formData()
    const file = formData.get('file') as File | null
    
    if (!file) {
      return NextResponse.json(
        { success: false, error: 'No file provided' },
        { status: 400 }
      )
    }
    
    // Get file buffer
    const arrayBuffer = await file.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)
    
    // Create FormData for FastAPI using node-fetch compatible format
    // We'll use a manual multipart/form-data approach or simple fetch
    const fastapiFormData = new FormData()
    const blob = new Blob([buffer], { type: file.type || 'image/jpeg' })
    fastapiFormData.append('file', blob, file.name || 'frame.jpg')
    
    // Send request to FastAPI backend
    const response = await fetch(`${FASTAPI_URL}/capture`, {
      method: 'POST',
      body: fastapiFormData,
      // Don't set Content-Type header - let fetch set it with boundary
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
      const errorMsg = errorData.error || 'Backend error'
      
      // Enhance error message based on status code
      let friendlyError = errorMsg
      if (response.status === 413) {
        friendlyError = `File too large: ${errorMsg}. Please use a smaller image.`
      } else if (response.status >= 500) {
        friendlyError = `Server error: ${errorMsg}. Please try again or contact support.`
      } else if (response.status === 400) {
        friendlyError = `Invalid request: ${errorMsg}. Please check the input.`
      }
      
      return NextResponse.json(
        { success: false, error: friendlyError },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data)
    
  } catch (error) {
    console.error('Error in capture API route:', error)
    return NextResponse.json(
      { success: false, error: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}

