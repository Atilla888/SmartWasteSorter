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
/**
 * Maps HTTP status codes to user-friendly error messages with troubleshooting hints.
 */
function getErrorMessage(status: number, errorText: string): string {
  switch (status) {
    case 400:
      if (errorText.includes('IP address')) {
        return `Invalid IP address. Please check that the IP address is correct (e.g., 192.168.0.105). Error: ${errorText}`
      }
      return `Invalid request: ${errorText}. Please check the input and try again.`
    
    case 503:
      if (errorText.includes('connect') || errorText.includes('DroidCam')) {
        return `Cannot connect to camera. Troubleshooting: 1) Check camera is powered on, 2) Verify IP address is correct, 3) Ensure camera and computer are on the same network, 4) Make sure DroidCam app is running. Error: ${errorText}`
      }
      if (errorText.includes('timeout')) {
        return `Camera connection timed out. The camera may be busy or unreachable. Please try again. Error: ${errorText}`
      }
      return `Service unavailable: ${errorText}. Please try again in a moment.`
    
    case 500:
      if (errorText.includes('JPEG') || errorText.includes('frame')) {
        return `Failed to extract frame from camera stream. The camera stream may be corrupted. Please try again. Error: ${errorText}`
      }
      return `Server error: ${errorText}. Please try again or contact support if the issue persists.`
    
    default:
      return `Request failed (${status}): ${errorText}. Please try again.`
  }
}

export async function captureFrame(ip: string): Promise<Blob> {
  if (!ip || !ip.trim()) {
    throw new Error('Camera IP address is required. Please enter a valid IP address.')
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
    const friendlyMessage = getErrorMessage(response.status, errorText)
    throw new Error(friendlyMessage)
  }

  const blob = await response.blob()
  
  // Verify we got an image blob
  if (!blob.type.startsWith('image/')) {
    throw new Error(`Invalid response: expected image, got ${blob.type}. The server may have returned an error page instead of an image.`)
  }

  return blob
}

