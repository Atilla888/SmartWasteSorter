# Frontend Code Explanation

This document provides a detailed component-by-component and function-by-function explanation of the frontend source code.

---

## Table of Contents

1. [App Structure](#app-structure)
2. [Main Components](#main-components)
3. [API Routes (Next.js)](#api-routes-nextjs)
4. [Utility Functions](#utility-functions)
5. [System Interactions](#system-interactions)

---

## App Structure

### app/layout.tsx

**Purpose:** Root layout component that wraps all pages. Sets up fonts, metadata, and global styles.

**Role:** Provides the HTML structure and global configuration for the Next.js application.

**Key Elements:**
- **Font Setup:** Loads Geist Sans and Geist Mono fonts from Google Fonts
- **Metadata:** Sets page title and description (default Next.js values)
- **Global Styles:** Imports `globals.css` for Tailwind CSS configuration
- **Layout Structure:** Provides `<html>` and `<body>` tags with font variables

**State Management:** None (static layout component)

**Side Effects:**
- Loads Google Fonts (external resource)
- Applies global CSS styles

**System Workflow:**
- Rendered once on initial page load
- Wraps all page content
- Provides font variables via CSS classes

---

### app/page.tsx

**Purpose:** Main page component that renders the home page.

**Role:** Entry point for the application. Renders the main UI component.

**Key Elements:**
- **Component:** Renders `SplineSceneBasic` component (from `components/ui/demo.tsx`)
- **Layout:** Wraps content in `<main>` tag with minimum height styling

**State Management:** None (presentational component)

**System Workflow:**
- Next.js renders this component at route `/`
- Delegates all UI logic to `SplineSceneBasic` component

---

## Main Components

### components/ui/demo.tsx - Main Control Panel

**Purpose:** Primary UI component containing the control panel, camera connection, and frame capture functionality.

**Role:** Central component that manages user interactions, camera state, and coordinates the capture workflow.

#### State Variables

**`cameraIp: string`**
- **Purpose:** Stores the DroidCam IP address entered by user
- **Initial Value:** `""` (empty string)
- **Modified By:** User input in IP address field
- **Used By:** Camera connection, frame capture

**`isCameraConnected: boolean`**
- **Purpose:** Tracks whether camera is currently connected
- **Initial Value:** `false`
- **Modified By:** `handleConnectCamera()`, `handleDisconnectCamera()`
- **Used By:** Controls button text, input field disabled state, CameraFeed visibility

**`streamKey: number | null`**
- **Purpose:** Key prop for CameraFeed component to force remount on connect/disconnect
- **Initial Value:** `null`
- **Modified By:** `handleConnectCamera()` (sets to `Date.now()`), `handleDisconnectCamera()` (sets to `null`)
- **Used By:** CameraFeed component key prop

**`error: string | null`**
- **Purpose:** Stores validation error messages
- **Initial Value:** `null`
- **Modified By:** `handleConnectCamera()`, input onChange handler
- **Used By:** Error alert display

**`isCapturing: boolean`**
- **Purpose:** Tracks whether frame capture is in progress
- **Initial Value:** `false`
- **Modified By:** `handleCaptureAndSend()`
- **Used By:** Disables capture button, shows loading state

**`captureStatus: string`**
- **Purpose:** Status message for capture operation
- **Initial Value:** `""` (empty string)
- **Modified By:** `handleCaptureAndSend()`, `handleDisconnectCamera()`
- **Used By:** Displays capture progress and results

**`previewPaused: boolean`**
- **Purpose:** Controls whether camera preview is paused (to release MJPEG connection)
- **Initial Value:** `false`
- **Modified By:** `handleCaptureAndSend()` (sets to `true`, then `false` in finally)
- **Used By:** Passed to CameraFeed component as `paused` prop

#### Functions

##### `validateIpAddress(ip: string): boolean`

**Purpose:** Validates IP address format using regex pattern.

**Inputs:**
- `ip` (string): IP address to validate

**Outputs:**
- `boolean`: True if valid IP format, False otherwise

**Side Effects:** None (pure function)

**Trigger:** Called by `handleConnectCamera()` before connecting

**State Read:** None

**State Modified:** None

**System Workflow:**
- Validates IP format before attempting connection
- Uses regex: `/^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/`
- Returns false for empty strings or invalid formats

---

##### `handleConnectCamera(): void`

**Purpose:** Handles camera connect/disconnect button click. Validates IP and toggles connection state.

**Inputs:** None (reads from state)

**Outputs:** None (modifies state)

**Side Effects:**
- **State Changes:**
  - Clears `error` state
  - If connecting: Sets `isCameraConnected = true`, `streamKey = Date.now()`
  - If disconnecting: Calls `handleDisconnectCamera()`

**Trigger:** 
- User clicks "Connect" or "Disconnect" button
- User presses Enter key in IP input field

**State Read:**
- `cameraIp` - IP address value
- `isCameraConnected` - Current connection status

**State Modified:**
- `error` - Cleared on action
- `isCameraConnected` - Toggled based on current state
- `streamKey` - Set to timestamp when connecting

**System Workflow:**
1. Clears any existing error
2. Validates IP address is not empty
3. Validates IP format using `validateIpAddress()`
4. If validation fails, sets error message and returns
5. If already connected, calls `handleDisconnectCamera()`
6. If not connected, sets connection state and generates new stream key
7. New stream key forces CameraFeed to remount with fresh connection

**Backend Calls:** None (connection handled by CameraFeed component)

---

##### `handleDisconnectCamera(): Promise<void>`

**Purpose:** Handles camera disconnection. Cleans up state and waits for MJPEG connection to close.

**Inputs:** None

**Outputs:** `Promise<void>` (async function)

**Side Effects:**
- **State Changes:**
  - Sets `isCameraConnected = false`
  - Clears `error` and `captureStatus`
  - Waits 120ms for cleanup
  - Sets `streamKey = null` (allows remount on next connect)

**Trigger:** Called by `handleConnectCamera()` when disconnecting

**State Read:** None

**State Modified:**
- `isCameraConnected` - Set to `false`
- `error` - Cleared
- `captureStatus` - Cleared
- `streamKey` - Set to `null` after delay

**System Workflow:**
1. Sets `isCameraConnected = false` (hides CameraFeed component)
2. Clears error and capture status
3. Waits 120ms for CameraFeed cleanup to complete (MJPEG connection closure)
4. Resets `streamKey` to `null` (allows fresh remount on next connect)
5. Keeps `cameraIp` value for easy reconnection

**Backend Calls:** None

**Why 120ms Delay:**
- Allows CameraFeed cleanup function to execute
- Ensures MJPEG TCP connection is fully closed before remount
- Prevents connection conflicts on rapid connect/disconnect

---

##### `handleCaptureAndSend(): Promise<void>`

**Purpose:** Main capture workflow. Pauses preview, captures frame, uploads to backend, displays results.

**Inputs:** None (reads from state)

**Outputs:** `Promise<void>` (async function)

**Side Effects:**
- **State Changes:**
  - Sets `isCapturing = true` at start, `false` in finally
  - Updates `captureStatus` with progress messages
  - Sets `previewPaused = true` during capture, `false` in finally
- **Network I/O:**
  - Calls `/api/snapshot?ip={ip}` to get frame
  - Calls `/api/capture` to upload frame and trigger processing
- **Console Output:** Logs backend response for debugging

**Trigger:** User clicks "Capture & Send" button

**State Read:**
- `isCameraConnected` - Checks if camera is connected
- `cameraIp` - IP address for frame capture

**State Modified:**
- `isCapturing` - Set to `true` during operation, `false` in finally
- `captureStatus` - Updated with progress messages
- `previewPaused` - Set to `true` during capture, `false` in finally

**System Workflow:**
1. **Validation:**
   - Checks if camera is connected (returns if not)
   - Checks if IP address exists (returns if not)

2. **Preview Pause:**
   - Sets `isCapturing = true` (disables button)
   - Sets `captureStatus = "Pausing preview..."`
   - Sets `previewPaused = true` (releases MJPEG connection)

3. **Wait Period:**
   - Waits 250ms for DroidCam to free the stream connection
   - Updates status: `"Capturing frame..."`

4. **Frame Capture:**
   - Calls `captureFrame(cameraIp.trim())` which requests `/api/snapshot`
   - Receives JPEG blob from backend

5. **Image Upload:**
   - Updates status: `"Uploading..."`
   - Creates FormData with image blob
   - POSTs to `/api/capture` endpoint

6. **Result Display:**
   - Parses JSON response from backend
   - Extracts `prediction`, `confidence`, `saved_as`
   - Formats confidence as percentage
   - Updates `captureStatus` with success message or error

7. **Cleanup (finally block):**
   - Sets `isCapturing = false` (re-enables button)
   - Sets `previewPaused = false` (resumes preview)

**Backend Calls:**
- `GET /api/snapshot?ip={ip}` - Frame extraction (via `captureFrame()`)
- `POST /api/capture` - Image upload and processing

**Error Handling:**
- Catches all exceptions
- Updates `captureStatus` with error message
- Always resumes preview in finally block (prevents stuck state)

**Why Preview Pause:**
- DroidCam Free allows only one connection to `/video` stream
- Preview and capture cannot run simultaneously
- Solution: Pause preview, capture frame, resume preview

---

#### Component Render Logic

**Conditional Rendering:**
- **CameraFeed:** Only rendered when `isCameraConnected && streamKey !== null`
- **Error Alert:** Only rendered when `error !== null`
- **Capture Status:** Only rendered when `captureStatus !== ""`

**Key Props:**
- **CameraFeed:** Receives `ipAddress={cameraIp.trim()}`, `paused={previewPaused}`, `key={streamKey}`
- **Input Field:** Disabled when `isCameraConnected === true`
- **Connect Button:** Text changes based on `isCameraConnected`
- **Capture Button:** Disabled when `!isCameraConnected || isCapturing`

---

### components/sorter/CameraFeed.tsx - Camera Preview Component

**Purpose:** Displays live MJPEG video stream from DroidCam. Handles connection, loading states, errors, and pause/resume functionality.

**Role:** Manages the camera preview stream, handles connection lifecycle, and supports pause mechanism for frame capture.

#### Props

**`ipAddress: string`** (required)
- **Purpose:** DroidCam IP address for stream URL
- **Used By:** Constructs stream URL: `http://{ipAddress}:4747/video`

**`paused?: boolean`** (optional, default: `false`)
- **Purpose:** Controls whether preview is paused (releases MJPEG connection)
- **Used By:** Determines if stream URL is empty string (paused) or actual URL

#### State Variables

**`isLoading: boolean`**
- **Purpose:** Tracks loading state of stream
- **Initial Value:** `true`
- **Modified By:** `handleImageLoad()`, `handleImageError()`, useEffect
- **Used By:** Shows loading spinner

**`hasError: boolean`**
- **Purpose:** Tracks connection error state
- **Initial Value:** `false`
- **Modified By:** `handleImageError()`, useEffect cleanup
- **Used By:** Shows error message and retry button

**`retryCount: number`**
- **Purpose:** Counter to force component remount on retry
- **Initial Value:** `0`
- **Modified By:** `handleRetry()` (increments)
- **Used By:** useEffect dependency (triggers remount)

**`abortControllerRef: RefObject<AbortController | null>`**
- **Purpose:** Stores AbortController for request cancellation
- **Initial Value:** `null`
- **Modified By:** useEffect (creates new controller)
- **Used By:** Cleanup function to abort requests

**`imgRef: RefObject<HTMLImageElement | null>`**
- **Purpose:** Reference to `<img>` element for direct manipulation
- **Initial Value:** `null`
- **Modified By:** React ref assignment
- **Used By:** Direct src manipulation for pause/resume

**`timestampRef: RefObject<number>`**
- **Purpose:** Timestamp for stream URL cache busting
- **Initial Value:** `Date.now()`
- **Modified By:** `handleRetry()` (updates to new timestamp)
- **Used By:** Stream URL query parameter

#### Computed Values

**`streamUrl: string`**
- **Purpose:** MJPEG stream URL or empty string if paused
- **Computed:** `paused ? "" : "http://${ipAddress}:4747/video?ts=${timestampRef.current}"`
- **Used By:** `<img src={streamUrl}>`

#### Functions

##### `handleImageLoad(): void`

**Purpose:** Handles successful image load event. Indicates stream is connected and displaying.

**Inputs:** None (event handler)

**Outputs:** None

**Side Effects:**
- **State Changes:**
  - Sets `isLoading = false`
  - Sets `hasError = false`

**Trigger:** Browser `onLoad` event on `<img>` element when stream starts

**State Read:**
- `abortControllerRef.current` - Checks if component is still mounted

**State Modified:**
- `isLoading` - Set to `false`
- `hasError` - Set to `false`

**System Workflow:**
- Called when MJPEG stream successfully loads
- Hides loading spinner
- Shows video feed
- Only updates state if component is still mounted and not aborted

---

##### `handleImageError(): void`

**Purpose:** Handles image load error. Indicates connection failure.

**Inputs:** None (event handler)

**Outputs:** None

**Side Effects:**
- **State Changes:**
  - Sets `isLoading = false`
  - Sets `hasError = true`

**Trigger:** Browser `onError` event on `<img>` element when stream fails

**State Read:**
- `abortControllerRef.current` - Checks if component is still mounted

**State Modified:**
- `isLoading` - Set to `false`
- `hasError` - Set to `true`

**System Workflow:**
- Called when MJPEG stream fails to load
- Hides loading spinner
- Shows error message and retry button
- Only updates state if component is still mounted and not aborted

---

##### `handleRetry(): void`

**Purpose:** Retries connection by generating new timestamp and incrementing retry counter.

**Inputs:** None

**Outputs:** None

**Side Effects:**
- **State Changes:**
  - Updates `timestampRef.current = Date.now()` (new timestamp)
  - Increments `retryCount` (triggers useEffect remount)

**Trigger:** User clicks "Retry Connection" button

**State Read:** None

**State Modified:**
- `timestampRef.current` - Updated to current timestamp
- `retryCount` - Incremented (via `setRetryCount(prev => prev + 1)`)

**System Workflow:**
1. Generates new timestamp for cache busting
2. Increments retry counter
3. Triggers useEffect (due to `retryCount` dependency)
4. Creates new stream connection with fresh URL

**Why New Timestamp:**
- Forces browser to make new request (bypasses cache)
- Ensures fresh connection attempt

---

#### useEffect Hook

**Purpose:** Manages stream connection lifecycle, pause/resume, and cleanup.

**Dependencies:** `[ipAddress, retryCount, paused]`

**Side Effects:**
- **State Changes:**
  - Sets `isLoading = true` on mount/change
  - Sets `hasError = false` on mount/change
  - Sets `imgRef.current.src = ""` when paused
- **Network I/O:**
  - Creates new AbortController for request cancellation
- **Cleanup:**
  - Sets `imgRef.current.src = "about:blank"` to close TCP connection
  - Removes event handlers
  - Aborts AbortController

**Trigger:**
- Component mount
- `ipAddress` changes
- `retryCount` changes
- `paused` prop changes

**System Workflow:**

**On Mount/Change:**
1. If `paused === true`:
   - Clears image src (releases MJPEG connection)
   - Sets loading state
   - Returns early (no stream connection)

2. If `paused === false`:
   - Creates new AbortController
   - Sets loading and error states
   - Image element loads stream URL (browser initiates connection)

**On Unmount/Cleanup:**
1. Removes `onload` and `onerror` handlers (prevents state updates during cleanup)
2. Sets `imgRef.current.src = "about:blank"` (forces browser to close TCP connection)
3. Aborts AbortController (cancels any pending requests)

**Why "about:blank":**
- Forces browser to close existing TCP connection to DroidCam
- Prevents connection leaks
- Ensures clean disconnection

**Why Remove Event Handlers:**
- Prevents state updates after component unmount
- Avoids React warnings about updating unmounted components

---

#### Component Render Logic

**Conditional Rendering:**
- **Loading Spinner:** Shown when `isLoading && !hasError`
- **Error Message:** Shown when `hasError === true`
- **Video Feed:** Shown when `!isLoading && !hasError` (hidden otherwise)

**Image Element:**
- **src:** `streamUrl` (empty string when paused, actual URL when active)
- **onLoad:** `handleImageLoad` (success handler)
- **onError:** `handleImageError` (error handler)
- **className:** Hidden when loading or error state

**Stream URL Format:**
- Active: `http://{ipAddress}:4747/video?ts={timestamp}`
- Paused: `""` (empty string)

**Why Timestamp Query Parameter:**
- Cache busting (forces fresh request)
- Prevents browser from using cached stream

---

## API Routes (Next.js)

### app/api/snapshot/route.ts

**Purpose:** Next.js API route that proxies snapshot requests to FastAPI backend. Extracts single frame from DroidCam MJPEG stream.

**Role:** Server-side proxy that forwards frame extraction requests to Python backend.

#### Function: `GET(req: NextRequest): Promise<NextResponse>`

**Purpose:** Handles GET requests for frame extraction. Proxies to FastAPI backend.

**Inputs:**
- `req` (NextRequest): Next.js request object

**Outputs:**
- `NextResponse`: HTTP response with JPEG image bytes or error JSON

**Side Effects:**
- **Network I/O:**
  - Makes GET request to FastAPI backend: `${FASTAPI_URL}/snapshot?ip={ip}`
  - Reads response as ArrayBuffer
- **Console Output:** Logs errors to console

**Trigger:** Frontend calls `GET /api/snapshot?ip={ip}`

**State Read:**
- `process.env.FASTAPI_URL` - Backend URL (defaults to `http://localhost:8000`)

**State Modified:** None

**System Workflow:**
1. Extracts `ip` query parameter from request URL
2. Validates IP parameter exists (returns 400 if missing)
3. Constructs FastAPI URL: `${FASTAPI_URL}/snapshot?ip={ip}`
4. Makes GET request to FastAPI backend
5. If error, returns JSON error response
6. If success, reads response as ArrayBuffer
7. Returns JPEG image with `Content-Type: image/jpeg` header

**Backend Calls:**
- `GET ${FASTAPI_URL}/snapshot?ip={ip}` - FastAPI frame extraction endpoint

**Error Handling:**
- Missing IP: Returns 400 with JSON error
- Backend error: Returns backend status code with error message
- Unexpected error: Returns 500 with error message

**Response Format:**
- Success: `Response` with ArrayBuffer body, `Content-Type: image/jpeg`
- Error: `NextResponse.json()` with `{error: string}`

**Why Proxy:**
- Avoids CORS issues (server-to-server communication)
- Allows Next.js to handle authentication/authorization if needed
- Provides consistent API interface for frontend

---

### app/api/capture/route.ts

**Purpose:** Next.js API route that proxies image upload requests to FastAPI backend. Handles multipart/form-data uploads.

**Role:** Server-side proxy that forwards image processing requests to Python backend.

#### Function: `POST(request: NextRequest): Promise<NextResponse>`

**Purpose:** Handles POST requests for image upload and processing. Proxies to FastAPI backend.

**Inputs:**
- `request` (NextRequest): Next.js request object with FormData body

**Outputs:**
- `NextResponse`: JSON response with processing results or error

**Side Effects:**
- **Network I/O:**
  - Reads FormData from request
  - Converts file to buffer
  - Creates new FormData for FastAPI
  - Makes POST request to FastAPI backend: `${FASTAPI_URL}/capture`
- **Console Output:** Logs errors to console

**Trigger:** Frontend calls `POST /api/capture` with FormData

**State Read:**
- `process.env.FASTAPI_URL` - Backend URL (defaults to `http://localhost:8000`)

**State Modified:** None

**System Workflow:**
1. Reads FormData from request body
2. Extracts `file` field from FormData
3. Validates file exists (returns 400 if missing)
4. Converts file to ArrayBuffer, then Buffer
5. Creates new Blob with file data
6. Creates new FormData and appends blob
7. POSTs to FastAPI backend: `${FASTAPI_URL}/capture`
8. If error, returns JSON error response
9. If success, returns JSON response from backend

**Backend Calls:**
- `POST ${FASTAPI_URL}/capture` - FastAPI image processing endpoint

**Error Handling:**
- Missing file: Returns 400 with JSON error
- Backend error: Returns backend status code with error message
- Unexpected error: Returns 500 with error message

**Response Format:**
- Success: `NextResponse.json()` with backend response:
  ```json
  {
    "success": true,
    "saved_as": "frame_20241121_143022_456.jpg",
    "prediction": "plastic",
    "confidence": 0.95,
    "robot_action": "Sorted to PLASTIC bin"
  }
  ```
- Error: `NextResponse.json()` with `{success: false, error: string}`

**Why Proxy:**
- Handles file conversion (Next.js File → FastAPI-compatible format)
- Avoids CORS issues
- Provides consistent API interface

**File Conversion:**
- Next.js provides `File` object
- Converts to `ArrayBuffer` then `Buffer`
- Creates new `Blob` for FastAPI compatibility
- Reconstructs FormData with blob

---

## Utility Functions

### lib/sorter/capture.ts

**Purpose:** Utility function for capturing frames from DroidCam via backend proxy.

**Role:** Provides clean interface for frame capture, abstracts backend API call.

#### Function: `captureFrame(ip: string): Promise<Blob>`

**Purpose:** Captures a single JPEG frame from DroidCam MJPEG stream via backend proxy.

**Inputs:**
- `ip` (string): DroidCam IP address

**Outputs:**
- `Promise<Blob>`: Resolves to Blob containing JPEG image bytes

**Side Effects:**
- **Network I/O:**
  - Makes GET request to `/api/snapshot?ip={ip}`
  - Reads response as Blob
- **Exception:** Throws Error if validation fails, request fails, or response is invalid

**Trigger:** Called by `handleCaptureAndSend()` in demo.tsx

**State Read:** None (pure function)

**State Modified:** None

**System Workflow:**
1. Validates IP address is not empty (throws if invalid)
2. Trims IP address whitespace
3. Makes GET request to `/api/snapshot?ip={ip}` (Next.js API route)
4. Checks response status (throws if not ok)
5. Reads response as Blob
6. Validates blob is an image type (throws if not)
7. Returns Blob

**Backend Calls:**
- `GET /api/snapshot?ip={ip}` - Next.js API route (proxies to FastAPI)

**Error Handling:**
- Empty IP: Throws `Error('Camera IP address is required')`
- Request failure: Throws `Error('Snapshot request failed: {status} {text}')`
- Invalid response: Throws `Error('Invalid response: expected image, got {type}')`

**Why Backend Proxy:**
- Avoids CORS issues (browser cannot directly access DroidCam)
- Works with DroidCam Free (no `/shot.jpg` endpoint)
- Backend handles MJPEG stream parsing

---

### lib/utils.ts

**Purpose:** Utility function for merging CSS class names with Tailwind CSS.

**Role:** Provides className merging utility for conditional styling.

#### Function: `cn(...inputs: ClassValue[]): string`

**Purpose:** Merges class names using `clsx` and `tailwind-merge` to handle Tailwind conflicts.

**Inputs:**
- `...inputs` (ClassValue[]): Variable number of class name arguments

**Outputs:**
- `string`: Merged class name string

**Side Effects:** None (pure function)

**Trigger:** Used throughout components for conditional className generation

**State Read:** None

**State Modified:** None

**System Workflow:**
1. Takes variable number of class name arguments
2. Passes to `clsx()` for conditional class merging
3. Passes result to `twMerge()` for Tailwind conflict resolution
4. Returns final merged class string

**Why twMerge:**
- Resolves Tailwind CSS class conflicts (e.g., `p-4 p-6` → `p-6`)
- Ensures last class wins for conflicting utilities

**Usage Example:**
```typescript
cn("base-class", condition && "conditional-class", "another-class")
```

---

## System Interactions

### User Action Flow

#### 1. Camera Connection Flow

**User Action:** Enters IP address and clicks "Connect"

**Frontend Flow:**
1. `handleConnectCamera()` validates IP
2. Sets `isCameraConnected = true`
3. Sets `streamKey = Date.now()` (forces remount)
4. CameraFeed component mounts with new key
5. CameraFeed useEffect runs, creates stream connection
6. Image element loads MJPEG stream URL
7. `handleImageLoad()` fires when stream connects
8. Preview displays live feed

**State Changes:**
- `isCameraConnected: false → true`
- `streamKey: null → timestamp`
- `isLoading: true → false` (in CameraFeed)
- `hasError: false` (in CameraFeed)

**Backend Calls:** None (direct browser connection to DroidCam)

**Disconnect Flow:**
1. User clicks "Disconnect"
2. `handleDisconnectCamera()` called
3. Sets `isCameraConnected = false` (hides CameraFeed)
4. CameraFeed cleanup runs, closes MJPEG connection
5. Waits 120ms for cleanup
6. Resets `streamKey = null`

---

#### 2. Frame Capture Flow

**User Action:** Clicks "Capture & Send" button

**Frontend Flow:**
1. `handleCaptureAndSend()` validates connection
2. Sets `isCapturing = true` (disables button)
3. Sets `previewPaused = true` (releases MJPEG connection)
4. Updates status: "Pausing preview..."
5. Waits 250ms for DroidCam to free stream
6. Updates status: "Capturing frame..."
7. Calls `captureFrame(ip)` which requests `/api/snapshot`
8. Next.js API route proxies to FastAPI backend
9. FastAPI extracts frame from MJPEG stream
10. Returns JPEG blob to frontend
11. Updates status: "Uploading..."
12. Creates FormData with image blob
13. POSTs to `/api/capture`
14. Next.js API route proxies to FastAPI backend
15. FastAPI processes image (saves, runs ML, triggers robot)
16. Returns JSON response with results
17. Frontend parses response, displays prediction and confidence
18. Sets `previewPaused = false` (resumes preview)
19. Sets `isCapturing = false` (re-enables button)

**State Changes:**
- `isCapturing: false → true → false`
- `previewPaused: false → true → false`
- `captureStatus: "" → "Pausing..." → "Capturing..." → "Uploading..." → "Success/Error message"`

**Backend Calls:**
- `GET /api/snapshot?ip={ip}` → FastAPI `/snapshot` (frame extraction)
- `POST /api/capture` → FastAPI `/capture` (image processing)

**Error Handling:**
- Any error caught in try-catch
- Error message displayed in `captureStatus`
- Preview always resumes in finally block

---

### Frontend → Backend Communication

**API Route Pattern:**
- Frontend calls Next.js API routes (`/api/*`)
- Next.js routes proxy to FastAPI backend (`http://localhost:8000/*`)
- FastAPI processes request and returns response
- Next.js routes forward response to frontend

**Why Proxy Pattern:**
- Avoids CORS issues (same-origin requests)
- Allows Next.js to handle authentication/authorization
- Provides consistent API interface
- Handles file format conversion

**Request Flow:**
```
Frontend Component
  ↓
Utility Function (capture.ts)
  ↓
Next.js API Route (/api/snapshot or /api/capture)
  ↓
FastAPI Backend (Python)
  ↓
Response back through same chain
```

---

### State Management Architecture

**Component-Level State:**
- Each component manages its own state via `useState` hooks
- No global state management library (Redux, Zustand, etc.)
- State passed via props between components

**State Flow:**
- **demo.tsx:** Manages camera connection, capture workflow, preview pause
- **CameraFeed.tsx:** Manages stream connection, loading, errors

**State Synchronization:**
- `previewPaused` prop passed from demo.tsx to CameraFeed
- CameraFeed reacts to `paused` prop change via useEffect
- Stream URL computed based on `paused` prop

---

### Error Handling Patterns

**Validation Errors:**
- Handled immediately in event handlers
- Displayed in error alert component
- Prevent action execution

**Network Errors:**
- Caught in try-catch blocks
- Displayed in status messages
- Do not crash application

**Component Errors:**
- CameraFeed handles connection errors gracefully
- Shows error UI with retry button
- Allows user to retry without page reload

---

### Performance Considerations

**Stream Management:**
- Single MJPEG connection at a time (DroidCam limitation)
- Preview paused during capture to release connection
- Cleanup ensures connections are closed properly

**Component Remounting:**
- `streamKey` prop forces CameraFeed remount on connect/disconnect
- Ensures fresh connection state
- Prevents stale connections

**Cache Busting:**
- Timestamp query parameter in stream URL
- Forces fresh request on retry
- Prevents browser caching issues

---

## Summary

The frontend is organized into clear layers:

1. **App Layer** (`app/`): Next.js routing and layout
2. **Component Layer** (`components/`): React components for UI
3. **API Layer** (`app/api/`): Next.js API routes that proxy to FastAPI
4. **Utility Layer** (`lib/`): Helper functions for common operations

Key design patterns:
- **Component State:** Local state management via React hooks
- **Prop Drilling:** State passed via props (no global state)
- **API Proxying:** Next.js routes proxy to FastAPI backend
- **Error Handling:** Try-catch with user-friendly error messages
- **Async Operations:** Async/await for network requests

The system integrates:
- **User Interface:** React components with Tailwind CSS
- **Camera Streaming:** Direct browser connection to DroidCam MJPEG
- **Backend Communication:** Next.js API routes → FastAPI backend
- **State Management:** React hooks for component state

All components work together to provide a seamless user experience for camera connection, frame capture, and result display.
