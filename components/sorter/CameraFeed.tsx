'use client'

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { RefreshCw, AlertCircle, Video } from "lucide-react"
import { cn } from "@/lib/utils"

interface CameraFeedProps {
  ipAddress: string
  paused?: boolean
}

export function CameraFeed({ ipAddress, paused = false }: CameraFeedProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const abortControllerRef = useRef<AbortController | null>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const timestampRef = useRef<number>(Date.now())

  // Generate stream URL - empty string when paused to release MJPEG connection
  const streamUrl = paused
    ? ""
    : `http://${ipAddress}:4747/video?ts=${timestampRef.current}`

  useEffect(() => {
    // Handle pause/unpause - release MJPEG connection when paused
    if (paused && imgRef.current) {
      // When paused, clear the src to release the MJPEG connection
      imgRef.current.src = ""
      setIsLoading(true)
      setHasError(false)
      return
    }

    // Create new AbortController for this connection
    abortControllerRef.current = new AbortController()
    const controller = abortControllerRef.current

    setIsLoading(true)
    setHasError(false)

    // Cleanup function to abort connection on unmount
    return () => {
      // CRITICAL: Force image to load "about:blank" to drop MJPEG TCP connection
      // This must happen BEFORE unmount to ensure browser closes the socket
      if (imgRef.current) {
        // Remove event handlers first to prevent state updates during cleanup
        imgRef.current.onload = null
        imgRef.current.onerror = null
        // Force browser to drop TCP connection by loading invalid URL
        imgRef.current.src = 'about:blank'
      }

      // Abort any ongoing requests
      if (controller) {
        controller.abort()
      }
    }
  }, [ipAddress, retryCount, paused])

  const handleImageLoad = () => {
    // Check if component is still mounted and not aborted
    if (abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
      setIsLoading(false)
      setHasError(false)
    }
  }

  const handleImageError = () => {
    // Check if component is still mounted and not aborted
    if (abortControllerRef.current && !abortControllerRef.current.signal.aborted) {
      setIsLoading(false)
      setHasError(true)
    }
  }

  const handleRetry = () => {
    // Generate new timestamp for retry to force fresh connection
    timestampRef.current = Date.now()
    setRetryCount(prev => prev + 1)
  }

  return (
    <div className="w-full p-8 relative z-10">
      <Card className="max-w-6xl mx-auto bg-neutral-900/50 border-neutral-800 backdrop-blur-sm shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl font-semibold text-neutral-100 flex items-center gap-2">
            <Video className="h-5 w-5" />
            Camera Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative w-full aspect-video bg-neutral-950 rounded-lg overflow-hidden border border-neutral-800">
            {isLoading && !hasError && (
              <div className="absolute inset-0 flex items-center justify-center bg-neutral-950">
                <div className="flex flex-col items-center gap-3">
                  <RefreshCw className="h-8 w-8 text-neutral-400 animate-spin" />
                  <p className="text-sm text-neutral-400">Connecting to camera...</p>
                </div>
              </div>
            )}

            {hasError && (
              <div className="absolute inset-0 flex items-center justify-center bg-neutral-950">
                <div className="flex flex-col items-center gap-4 p-6">
                  <AlertCircle className="h-12 w-12 text-destructive" />
                  <div className="text-center">
                    <p className="text-neutral-300 font-medium mb-2">
                      Failed to connect to camera
                    </p>
                    <p className="text-sm text-neutral-400 mb-4">
                      Unable to load stream from {ipAddress}:4747
                    </p>
                    <Button
                      onClick={handleRetry}
                      variant="outline"
                      size="sm"
                      className="gap-2"
                    >
                      <RefreshCw className="h-4 w-4" />
                      Retry Connection
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <img
              id="camera-stream"
              ref={imgRef}
              src={streamUrl}
              alt="Camera feed"
              onLoad={handleImageLoad}
              onError={handleImageError}
              className={cn(
                "w-full h-full object-contain",
                (isLoading || hasError) && "hidden"
              )}
            />
          </div>

          {!hasError && !isLoading && (
            <div className="mt-4 text-sm text-neutral-400">
              <p>Stream URL: <code className="text-neutral-300">{streamUrl}</code></p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

