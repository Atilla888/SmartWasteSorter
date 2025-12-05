# Smart Waste Sorter - Complete Implementation Guide

This document consolidates all implementation details for the Smart Waste Sorter project.

---

## 📋 Table of Contents

1. [Phase 1: Backend Camera Service & Frontend Capture](#phase-1-backend-camera-service--frontend-capture)
2. [Phase 2: Backend Snapshot Proxy](#phase-2-backend-snapshot-proxy)
3. [Phase 3: Preview Pause Implementation](#phase-3-preview-pause-implementation)
4. [File Structure](#file-structure)
5. [Testing Guide](#testing-guide)
6. [Troubleshooting](#troubleshooting)

---

## Phase 1: Backend Camera Service & Frontend Capture

### Problem
Initial implementation required a way to capture frames from DroidCam and save them to the backend.

### Solution
- Backend FastAPI service with `/capture` endpoint
- Frontend capture utility using HTML5 Canvas
- Image upload pipeline from frontend to backend

### Files Created/Modified

#### Backend (FastAPI)
1. **`backend/main.py`**
   - FastAPI application with CORS middleware
   - `POST /capture` endpoint for receiving image uploads

2. **`backend/services/camera_service.py`**
   - `process_frame()` function: processes uploaded images
   - Saves frames to `backend/frames/` directory
   - Includes TODO comment for ML model integration (Phase 3)
   - Returns JSON response with success status and filename

3. **`backend/utils/image_utils.py`**
   - `read_upload_image()` utility function
   - Converts UploadFile to PIL Image (RGB format)

4. **`backend/requirements.txt`**
   - FastAPI dependencies
   - Pillow for image processing

#### Frontend (Next.js)
1. **`app/api/capture/route.ts`** (NEW)
   - Next.js API route that proxies to FastAPI backend
   - Handles multipart/form-data uploads

2. **`lib/sorter/capture.ts`** (NEW)
   - `captureFrame()` utility function
   - Initially used HTML5 Canvas (later changed to backend proxy)

3. **`components/sorter/CameraFeed.tsx`** (MODIFIED)
   - Added `id="camera-stream"` to `<img>` element
   - Maintains existing ref functionality

4. **`components/ui/demo.tsx`** (MODIFIED)
   - Added "Capture & Send" button to Control Panel
   - Added state management for capture status
   - Implemented `handleCaptureAndSend()` function

---

## Phase 2: Backend Snapshot Proxy

### Problem
DroidCam Free doesn't support `/shot.jpg`, and browser CORS prevents canvas extraction from MJPEG streams, causing "tainted canvas" errors.

### Solution
Backend snapshot proxy that extracts frames from MJPEG stream server-side, eliminating all CORS issues.

### Files Created/Modified

#### Backend
1. **`backend/services/snapshot_service.py`** (NEW)
   - `extract_single_frame(ip)` function
   - Connects to DroidCam MJPEG stream at `http://{ip}:4747/video`
   - Extracts first JPEG frame by finding SOI/EOI markers:
     - JPEG_START = `b'\xff\xd8'` (Start of Image)
     - JPEG_END = `b'\xff\xd9'` (End of Image)
   - Returns JPEG bytes

2. **`backend/main.py`** (UPDATED)
   - Added `GET /snapshot` endpoint
   - Accepts `ip` query parameter
   - Returns JPEG image with `image/jpeg` content-type
   - Error handling for connection/timeout issues

3. **`backend/requirements.txt`** (UPDATED)
   - Added `httpx==0.25.0` for async HTTP streaming

#### Frontend
1. **`app/api/snapshot/route.ts`** (NEW)
   - Next.js API route that proxies snapshot requests
   - Forwards IP parameter to FastAPI backend
   - Returns JPEG image response

2. **`lib/sorter/capture.ts`** (UPDATED)
   - Changed from: `fetch("http://IP:4747/shot.jpg")`
   - To: `fetch("/api/snapshot?ip={ip}")`
   - Backend handles MJPEG extraction server-side

### Architecture Flow

```
Frontend → GET /api/snapshot?ip={ip}
    ↓
Next.js API Route (app/api/snapshot/route.ts)
    ↓
FastAPI Backend → GET /snapshot?ip={ip}
    ↓
snapshot_service.extract_single_frame(ip)
    ↓
Connects to: http://{ip}:4747/video (MJPEG stream)
    ↓
Extracts first JPEG frame (SOI → EOI)
    ↓
Returns JPEG bytes → Frontend receives Blob
    ↓
Uploads to: POST /api/capture
    ↓
Saved to: backend/frames/
```

---

## Phase 3: Preview Pause Implementation

### Problem
DroidCam Free only allows ONE connection to `/video` at a time. When both the preview and the backend snapshot proxy try to connect simultaneously, DroidCam returns "Busy or Unavailable" error.

### Solution
Temporarily pause the MJPEG preview when capturing a snapshot, releasing the stream connection so the backend can connect successfully.

### Files Modified

1. **`components/sorter/CameraFeed.tsx`** (MODIFIED)
   - Added `paused?: boolean` prop to interface
   - Modified `streamUrl` to return empty string when paused
   - Updated `useEffect` to handle pause/unpause
   - When paused: sets img src to empty string, releasing MJPEG connection

2. **`components/ui/demo.tsx`** (MODIFIED)
   - Added `previewPaused` state
   - Modified `handleCaptureAndSend()` with pause/resume flow:
     1. Pause preview (`setPreviewPaused(true)`)
     2. Wait 250ms for DroidCam to free the stream
     3. Capture frame via backend proxy
     4. Upload frame to backend
     5. Resume preview (`setPreviewPaused(false)`) in finally block
   - Passes `paused={previewPaused}` prop to CameraFeed

### How It Works

**Normal State (Preview Active):**
- Frontend → MJPEG Stream (`http://{ip}:4747/video`)
- Preview displays live feed

**Capture State (Preview Paused):**
1. User clicks "Capture & Send"
2. `setPreviewPaused(true)` → CameraFeed receives `paused=true`
3. `streamUrl` becomes `""` → img src = `""` (releases MJPEG connection)
4. Wait 250ms (allow DroidCam to free stream)
5. Backend snapshot proxy connects to `/video` successfully
6. Frame extracted and returned
7. Upload to backend
8. `setPreviewPaused(false)` → Preview resumes automatically

---

## File Structure

### Backend Files

```
backend/
├── main.py                      # FastAPI app with /capture and /snapshot endpoints
├── requirements.txt             # Dependencies (FastAPI, Pillow, httpx)
├── services/
│   ├── camera_service.py       # process_frame() - saves uploaded images
│   └── snapshot_service.py     # extract_single_frame() - extracts from MJPEG
├── utils/
│   └── image_utils.py          # read_upload_image() - converts to PIL Image
└── frames/                     # Directory for saved frames (auto-created)
```

### Frontend Files

```
app/
├── api/
│   ├── capture/
│   │   └── route.ts            # Proxy to FastAPI /capture endpoint
│   └── snapshot/
│       └── route.ts            # Proxy to FastAPI /snapshot endpoint
├── components/
│   ├── sorter/
│   │   └── CameraFeed.tsx      # MJPEG preview with pause support
│   └── ui/
│       └── demo.tsx            # Control Panel with capture button
└── lib/
    └── sorter/
        └── capture.ts          # captureFrame() - calls /api/snapshot
```

---

## Testing Guide

### Prerequisites

1. **Install Backend Dependencies:**
   ```bash
   cd backend
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies:**
   ```bash
   npm install
   ```

### Quick Test (Backend Only)

1. **Start Backend:**
   ```bash
   python main.py
   # or
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test Snapshot Endpoint:**
   ```bash
   curl "http://localhost:8000/snapshot?ip=192.168.0.105" --output test.jpg
   ```
   **Expected:** `test.jpg` is a valid JPEG image

### Full Integration Test

1. **Start Backend:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend:**
   ```bash
   npm run dev
   ```

3. **Test Workflow:**
   - Open `http://localhost:3000`
   - Enter DroidCam IP address in Control Panel
   - Click "Connect" button
   - **Expected:** MJPEG preview appears and shows live feed
   - Click "Capture & Send" button
   - **Expected Behavior:**
     - Preview briefly pauses (~250ms)
     - Status shows: "Pausing preview..." → "Capturing frame..." → "Uploading..."
     - Preview resumes automatically
     - Success message: `✓ Image sent successfully! Saved as: frame_XXXXXX.jpg`
     - Image saved in `backend/frames/`

4. **Verify Saved Frame:**
   - Check `backend/frames/` directory
   - You should see a new file: `frame_YYYYMMDD_HHMMSS_mmm.jpg`

---

## Troubleshooting

### Backend Issues

**"Failed to connect to DroidCam"**
- Verify DroidCam is running on phone
- Check IP address is correct
- Ensure phone and computer are on same WiFi network
- Verify DroidCam server is listening on port 4747

**"No JPEG frame found in stream"**
- DroidCam might be slow to start streaming
- Try again after a few seconds
- Check DroidCam app shows green "connected" status

**"Incomplete JPEG frame"**
- Network might be slow
- Try increasing timeout in `snapshot_service.py`
- Verify stable WiFi connection

### Frontend Issues

**Preview Doesn't Resume**
- Check browser console for errors
- Verify `previewPaused` state resets in finally block
- Try disconnecting and reconnecting camera

**Still Getting "DroidCam Busy" Errors**
- Increase delay: Change `250` to `500` in `demo.tsx`
- Check network latency between devices
- Verify DroidCam is actually releasing the connection

**CORS Errors**
- Verify backend is running on port 8000
- Check CORS settings in `backend/main.py`
- Ensure FASTAPI_URL environment variable is correct

### Capture Issues

**"Failed to fetch snapshot"**
- Verify backend is running and accessible
- Check backend logs for errors
- Test snapshot endpoint directly with curl

**Images Not Saving**
- Check file permissions on `backend/frames/` directory
- Verify PIL/Pillow is installed correctly
- Check backend logs for error messages

---

## Saved Frames

**Location:** `backend/frames/`

**Filename Format:** `frame_YYYYMMDD_HHMMSS_mmm.jpg`

**Example:** `frame_20241121_143022_456.jpg`

- **YYYYMMDD**: Date (Year-Month-Day)
- **HHMMSS**: Time (Hour-Minute-Second)
- **mmm**: Milliseconds (3 digits)

---

## API Endpoints

### FastAPI Backend

**POST** `/capture`
- Content-Type: `multipart/form-data`
- Body: `file: <image blob>`
- Response:
  ```json
  {
    "success": true,
    "saved_as": "frame_20241121_143022_456.jpg"
  }
  ```

**GET** `/snapshot?ip={ip}`
- Query Parameters: `ip` (required) - DroidCam IP address
- Response: JPEG image bytes with `Content-Type: image/jpeg`
- Example: `GET /snapshot?ip=192.168.0.105`

### Next.js API Routes

**POST** `/api/capture`
- Proxies to FastAPI backend
- Same request/response format as FastAPI

**GET** `/api/snapshot?ip={ip}`
- Proxies to FastAPI backend
- Returns JPEG image bytes

---

## Next Steps (Phase 4: ML Integration)

The implementation includes a placeholder comment in `backend/services/camera_service.py`:

```python
# TODO: run ML model here in Phase 3
```

This is where the ML model inference will be integrated.

---

**Last Updated:** November 21 2024  
**Status:** ✅ Complete and Ready for ML Integration

