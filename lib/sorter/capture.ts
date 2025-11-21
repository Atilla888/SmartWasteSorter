/**
 * Capture utility for capturing frames from DroidCam.
 * 
 * Uses backend snapshot proxy to extract a single frame from the MJPEG stream.
 * This avoids CORS issues and works with all DroidCam versions (including Free).
 * The MJPEG stream (/video) is used for preview only.
 */

/**
 * Captures a snapshot frame via backend proxy.
 * The backend extracts a single JPEG frame from the DroidCam MJPEG stream.
 * 
 * @param ip - DroidCam IP address
 * @returns Promise that resolves to a Blob containing the captured image
 * @throws Error if the fetch fails or IP is invalid
 */
export async function captureFrame(ip: string): Promise<Blob> {
  if (!ip || !ip.trim()) {
    throw new Error('Camera IP address is required')
  }

  // Request snapshot from backend proxy endpoint
  // Backend will extract a single frame from MJPEG stream
  const response = await fetch(
    `/api/snapshot?ip=${encodeURIComponent(ip.trim())}`,
    {
      method: "GET",
      cache: "no-store"
    }
  )

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText)
    throw new Error(`Snapshot request failed: ${response.status} ${errorText}`)
  }

  const blob = await response.blob()
  
  // Verify we got an image blob
  if (!blob.type.startsWith('image/')) {
    throw new Error('Invalid response: expected image, got ' + blob.type)
  }

  return blob
}

