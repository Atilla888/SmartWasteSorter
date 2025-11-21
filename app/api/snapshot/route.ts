import { NextRequest, NextResponse } from 'next/server'

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000'

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const ip = searchParams.get("ip")

    if (!ip) {
      return NextResponse.json(
        { error: "Missing IP parameter" },
        { status: 400 }
      )
    }

    // Proxy request to FastAPI backend
    const backendUrl = `${FASTAPI_URL}/snapshot?ip=${encodeURIComponent(ip)}`

    const res = await fetch(backendUrl, {
      method: "GET",
      cache: "no-store"
    })

    if (!res.ok) {
      const errorText = await res.text().catch(() => "Backend error")
      return NextResponse.json(
        { error: errorText },
        { status: res.status }
      )
    }

    // Get image bytes as ArrayBuffer
    const buf = await res.arrayBuffer()

    // Return JPEG image response
    return new Response(buf, {
      status: 200,
      headers: {
        "Content-Type": "image/jpeg",
        "Cache-Control": "no-store"
      }
    })

  } catch (error) {
    console.error('Error in snapshot API route:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    )
  }
}

