'use client'

import { useState } from "react"
import { SplineScene } from "@/components/ui/splite";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Spotlight } from "@/components/ui/spotlight"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Camera, AlertCircle, CameraOff } from "lucide-react"
import { CameraFeed } from "@/components/sorter/CameraFeed"
import { captureFrame } from "@/lib/sorter/capture"

// IP address validation regex
const IP_REGEX = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/

export function SplineSceneBasic() {
  const [cameraIp, setCameraIp] = useState("")
  const [isCameraConnected, setIsCameraConnected] = useState(false)
  const [streamKey, setStreamKey] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isCapturing, setIsCapturing] = useState(false)
  const [captureStatus, setCaptureStatus] = useState<string>("")
  const [previewPaused, setPreviewPaused] = useState(false)

  const validateIpAddress = (ip: string): boolean => {
    if (!ip.trim()) return false
    return IP_REGEX.test(ip.trim())
  }

  const handleConnectCamera = () => {
    setError(null)

    if (!cameraIp.trim()) {
      setError("Please enter a camera IP address")
      return
    }

    if (!validateIpAddress(cameraIp)) {
      setError("Please enter a valid IP address (e.g., 192.168.0.105)")
      return
    }

    if (isCameraConnected) {
      // Disconnect
      handleDisconnectCamera()
    } else {
      // Connect - generate new stream key to force remount
      setIsCameraConnected(true)
      setStreamKey(Date.now())
    }
  }

  const handleDisconnectCamera = async () => {
    // First, hide the camera feed (triggers cleanup in CameraFeed)
    setIsCameraConnected(false)
    setError(null)
    setCaptureStatus("") // Clear capture status on disconnect
    
    // Wait for cleanup to complete (image src set to "about:blank")
    // This ensures the MJPEG TCP connection is fully closed before remount
    await new Promise(res => setTimeout(res, 120))
    
    // Now reset streamKey to allow fresh remount on next connect
    setStreamKey(null)
    // Note: We keep cameraIp so user can easily reconnect
  }

  const handleCaptureAndSend = async () => {
    if (!isCameraConnected) {
      setCaptureStatus("Please connect camera first.")
      return
    }

    if (!cameraIp.trim()) {
      setCaptureStatus("Camera IP address is missing.")
      return
    }

    try {
      setIsCapturing(true)
      setCaptureStatus("Pausing preview...")

      // Step 1: Pause preview to release MJPEG connection
      setPreviewPaused(true)

      // Step 2: Wait for DroidCam to free the stream (250ms delay)
      await new Promise((res) => setTimeout(res, 250))

      // Step 3: Capture frame via backend proxy (extracts from MJPEG stream)
      setCaptureStatus("Capturing frame from camera...")
      const blob = await captureFrame(cameraIp.trim())

      // Step 4: Send to backend
      setCaptureStatus("Uploading image to server...")
      const formData = new FormData()
      formData.append("file", blob, "frame.jpg")

      setCaptureStatus("Processing image...")
      const res = await fetch("/api/capture", {
        method: "POST",
        body: formData
      })

      setCaptureStatus("Running ML inference...")
      const json = await res.json()
      
      // Debug logging
      console.log("Backend response:", json)

      if (json.success) {
        // Extract prediction and confidence from response
        const prediction = json.prediction || "unknown"
        const confidence = json.confidence || 0
        
        // Format confidence as percentage (e.g., 0.931 -> 93.1%)
        const confidencePercent = (confidence * 100).toFixed(1)
        
        // Show robot action status if available
        let statusMessage = `✓ Image processed successfully! Saved as: ${json.saved_as} | Prediction: ${prediction} (${confidencePercent}%)`
        if (json.robot_action) {
          statusMessage += ` | Robot: ${json.robot_action}`
        }
        
        setCaptureStatus(statusMessage)
      } else {
        // Enhanced error message with troubleshooting
        const errorMsg = json.error || "Unknown error"
        let friendlyError = `✗ Processing failed: ${errorMsg}`
        
        // Add troubleshooting hints based on error type
        if (errorMsg.includes("too large") || errorMsg.includes("File size")) {
          friendlyError += " | Tip: Try using a smaller image or compress the image before uploading."
        } else if (errorMsg.includes("decode") || errorMsg.includes("image format")) {
          friendlyError += " | Tip: Ensure the file is a valid image format (JPEG, PNG, etc.)."
        } else if (errorMsg.includes("model") || errorMsg.includes("ML")) {
          friendlyError += " | Tip: Check that the ML model file exists and is properly configured."
        } else if (errorMsg.includes("disk") || errorMsg.includes("permission")) {
          friendlyError += " | Tip: Check disk space and file permissions on the server."
        }
        
        setCaptureStatus(friendlyError)
      }

    } catch (err) {
      console.error(err)
      let errorMessage = "Unknown error occurred"
      
      if (err instanceof Error) {
        errorMessage = err.message
      } else if (typeof err === 'string') {
        errorMessage = err
      }
      
      // The error message from captureFrame already includes troubleshooting hints
      setCaptureStatus(`✗ Error: ${errorMessage}`)
    } finally {
      // Step 5: Resume preview after capture completes
      setIsCapturing(false)
      setPreviewPaused(false)
    }
  }

  return (
    <div className="w-full min-h-screen bg-black/[0.96] relative">
      {/* Hero Section with Spline */}
      <Card className="w-full h-[70vh] bg-black/[0.96] relative overflow-hidden border-0">
        <Spotlight
          className="-top-40 left-0 md:left-60 md:-top-20"
          fill="white"
        />
        
        <div className="flex h-full">
          {/* Left content */}
          <div className="flex-1 p-8 relative z-10 flex flex-col justify-center">
            <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 to-neutral-400">
              Smart Waste Sorter
            </h1>
            <p className="mt-4 text-neutral-300 max-w-lg">
              Yedige Mussabayev, Raiymbek Zhanuzak, Akerke Madiyarova, Atilla Kenebay, Altynkhan Imash
            </p>
          </div>

          {/* Right content */}
          <div className="flex-1 relative">
            <SplineScene 
              scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
              className="w-full h-full"
            />
          </div>
        </div>
      </Card>

      {/* Control Panel Section */}
      <div className="w-full p-8 relative z-10">
        <Card className="max-w-6xl mx-auto bg-neutral-900/50 border-neutral-800 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-2xl font-semibold text-neutral-100">
              Control Panel
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Manage camera connection, robot control, and system operations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="camera-ip" className="text-sm font-medium text-neutral-200">
                  DroidCam IP Address
                </label>
                <div className="flex gap-2">
                  <Input
                    id="camera-ip"
                    type="text"
                    placeholder="192.168.0.105"
                    value={cameraIp}
                    onChange={(e) => {
                      setCameraIp(e.target.value)
                      setError(null)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleConnectCamera()
                      }
                    }}
                    disabled={isCameraConnected}
                    className="flex-1 bg-neutral-800/50 border-neutral-700 text-neutral-100 placeholder:text-neutral-500 focus-visible:ring-neutral-600"
                  />
                  <Button
                    onClick={handleConnectCamera}
                    variant={isCameraConnected ? "secondary" : "default"}
                    size="lg"
                    className="gap-2"
                  >
                    <Camera className="h-4 w-4" />
                    {isCameraConnected ? "Disconnect" : "Connect"}
                  </Button>
                </div>
                <p className="text-xs text-neutral-500">
                  Example: 192.168.0.105
                </p>
              </div>

              {error && (
                <Alert variant="destructive" className="bg-destructive/10 border-destructive/50">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="text-destructive">
                    {error}
                  </AlertDescription>
                </Alert>
              )}

              {/* Capture & Send Section */}
              <div className="space-y-2 pt-4 border-t border-neutral-800">
                <label className="text-sm font-medium text-neutral-200">
                  Frame Capture
                </label>
                <div className="flex flex-col gap-2">
                  <Button
                    onClick={handleCaptureAndSend}
                    disabled={!isCameraConnected || isCapturing}
                    variant="outline"
                    size="lg"
                    className="gap-2"
                  >
                    {isCapturing ? (
                      <>
                        <AlertCircle className="h-4 w-4 animate-spin" />
                        Capturing...
                      </>
                    ) : (
                      <>
                        <CameraOff className="h-4 w-4" />
                        Capture & Send
                      </>
                    )}
                  </Button>
                  
                  {captureStatus && (
                    <p className={`text-sm ${
                      captureStatus.startsWith("✓") 
                        ? "text-green-400" 
                        : captureStatus.startsWith("✗")
                        ? "text-destructive"
                        : "text-neutral-400"
                    }`}>
                      {captureStatus}
                    </p>
                  )}
                </div>
                <p className="text-xs text-neutral-500">
                  Capture current frame from camera stream and send to backend for processing
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Camera Feed Section */}
      {isCameraConnected && streamKey !== null && (
        <CameraFeed 
          key={streamKey} 
          ipAddress={cameraIp.trim()}
          paused={previewPaused}
        />
      )}
    </div>
  )
}