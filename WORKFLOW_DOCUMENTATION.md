# Smart Waste Sorter - Complete Workflow Documentation

This document explains the complete end-to-end workflow of the Smart Waste Sorter system, from camera capture to robot sorting.

---

## 🔄 Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  User Interface (components/ui/demo.tsx)                 │  │
│  │  - Camera preview (MJPEG stream)                        │  │
│  │  - "Capture & Send" button                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 1. User clicks "Capture & Send"
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: Capture Frame from Camera                 │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ 1.1. Pause MJPEG preview
                             │ 1.2. Wait 250ms for stream release
                             │ 1.3. Call captureFrame(ip)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Next.js API Route: /api/snapshot                       │
│  (app/api/snapshot/route.ts)                                   │
│  - Proxies request to FastAPI backend                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ GET /api/snapshot?ip={ip}
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         FastAPI Backend: GET /snapshot                         │
│  (backend/main.py)                                             │
│  - Calls snapshot_service.extract_single_frame(ip)            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│      Snapshot Service: extract_single_frame()                  │
│  (backend/services/snapshot_service.py)                       │
│  - Connects to DroidCam MJPEG: http://{ip}:4747/video          │
│  - Extracts first JPEG frame (finds SOI/EOI markers)          │
│  - Returns JPEG bytes                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ JPEG image blob
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 2: Upload Image for Processing               │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ 2.1. Create FormData with image
                             │ 2.2. POST to /api/capture
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Next.js API Route: /api/capture                        │
│  (app/api/capture/route.ts)                                   │
│  - Receives FormData with image file                           │
│  - Proxies to FastAPI backend                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ POST /capture (multipart/form-data)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         FastAPI Backend: POST /capture                         │
│  (backend/main.py)                                             │
│  - Receives UploadFile                                         │
│  - Calls camera_service.process_frame(file)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 3: Process Frame & ML Inference              │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│      Camera Service: process_frame()                           │
│  (backend/services/camera_service.py)                        │
│                                                                 │
│  3.1. Decode image (read_upload_image)                        │
│  3.2. Generate timestamp filename                              │
│  3.3. Save to backend/frames/                                  │
│  3.4. Run ML inference (run_inference)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         ML Inference: run_inference()                          │
│  (backend/services/camera_service.py)                        │
│                                                                 │
│  - Load YOLO model (lazy loading, cached)                     │
│    Model path: backend/models/best.pt                          │
│  - Run inference: model(image)                                │
│  - Extract top-1 prediction and confidence                    │
│  - Returns: {prediction: "plastic", confidence: 0.95}        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Prediction result
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 4: Trigger Robot Sorting                     │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ sort_with_robot(prediction)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│      Dobot Service: sort_with_robot()                         │
│  (backend/services/dobot_service.py)                         │
│                                                                 │
│  4.1. Get singleton DobotService instance                      │
│  4.2. Auto-connect if not connected                           │
│  4.3. Call service.sort_item(class_name)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Robot Sorting Sequence: sort_item()                    │
│  (backend/services/dobot_service.py)                         │
│                                                                 │
│  Step 1: Move above pickup position                            │
│    → move_to(pickup_x, pickup_y, pickup_z + 20, pickup_r)     │
│                                                                 │
│  Step 2: Descend to pickup position                            │
│    → move_to(pickup_x, pickup_y, pickup_z - 30, pickup_r)     │
│                                                                 │
│  Step 3: Activate suction cup (pick)                           │
│    → SetEndEffectorSuctionCup(api, 1, 1)                      │
│                                                                 │
│  Step 4: Lift up                                                │
│    → move_to(pickup_x, pickup_y, pickup_z + 20, pickup_r)     │
│                                                                 │
│  Step 5: Move above bin position (based on class)              │
│    → Get bin position from BIN_POSITIONS[class_name]           │
│    → move_to(bin_x, bin_y, bin_z + 20, bin_r)                  │
│                                                                 │
│  Step 6: Descend to bin position                               │
│    → move_to(bin_x, bin_y, bin_z - 40, bin_r)                  │
│                                                                 │
│  Step 7: Deactivate suction cup (place)                         │
│    → SetEndEffectorSuctionCup(api, 1, 0)                      │
│                                                                 │
│  Step 8: Lift up                                                │
│    → move_to(bin_x, bin_y, bin_z + 20, bin_r)                  │
│                                                                 │
│  Step 9: Return home                                           │
│    → home() (SetHOMECmd or move_to(HOME_POSITION))            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Success/Error message
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 5: Return Response to Frontend               │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ JSON Response:
                             │ {
                             │   "success": true,
                             │   "saved_as": "frame_20241121_143022.jpg",
                             │   "prediction": "plastic",
                             │   "confidence": 0.95,
                             │   "robot_action": "moved to PLASTIC bin"
                             │ }
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                           │
│  - Display prediction and confidence                           │
│  - Display robot action status                                 │
│  - Resume MJPEG preview                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Detailed Step-by-Step Flow

### Phase 1: Image Capture

1. **User Action**: User clicks "Capture & Send" button in the UI
2. **Preview Pause**: Frontend pauses MJPEG preview stream
3. **Wait**: 250ms delay to allow DroidCam to free the stream
4. **Snapshot Request**: Frontend calls `captureFrame(ip)` which requests `/api/snapshot?ip={ip}`
5. **Backend Proxy**: Next.js API route forwards to FastAPI `/snapshot` endpoint
6. **Frame Extraction**: Backend connects to DroidCam MJPEG stream and extracts first JPEG frame
7. **Return Image**: JPEG blob returned to frontend

### Phase 2: Image Upload & Processing

8. **FormData Creation**: Frontend creates FormData with captured image
9. **Upload Request**: POST to `/api/capture` with image file
10. **Backend Reception**: FastAPI receives UploadFile
11. **Image Decoding**: Convert UploadFile to PIL Image (RGB format)
12. **File Saving**: Save image to `backend/frames/` with timestamp filename
13. **ML Model Loading**: Load YOLO classification model (cached after first load)
14. **Inference**: Run model prediction on image
15. **Result Extraction**: Get top-1 class name and confidence score

### Phase 3: Robot Sorting

16. **Robot Service Call**: Call `sort_with_robot(prediction)` with class name
17. **Connection Check**: Check if Dobot is connected, auto-connect if needed
18. **Bin Position Lookup**: Get bin coordinates from `BIN_POSITIONS` dictionary
19. **Movement Sequence**: Execute 9-step sorting sequence:
    - Move to pickup area
    - Descend to item
    - Activate suction cup
    - Lift item
    - Move to appropriate bin
    - Descend to bin
    - Release item
    - Lift up
    - Return home

### Phase 4: Response & Display

20. **Response Building**: Combine prediction, confidence, and robot action status
21. **JSON Return**: Return complete response to frontend
22. **UI Update**: Frontend displays results and resumes preview

---

## 🔧 Key Components

### Frontend Components

- **`components/ui/demo.tsx`**: Main UI with camera preview and capture button
- **`components/sorter/CameraFeed.tsx`**: MJPEG stream display component
- **`lib/sorter/capture.ts`**: Frame capture utility
- **`app/api/capture/route.ts`**: Next.js API route proxy
- **`app/api/snapshot/route.ts`**: Next.js snapshot proxy

### Backend Components

- **`backend/main.py`**: FastAPI application with endpoints
- **`backend/services/camera_service.py`**: Image processing and ML inference
- **`backend/services/snapshot_service.py`**: DroidCam frame extraction
- **`backend/services/dobot_service.py`**: Robot control and sorting
- **`backend/utils/image_utils.py`**: Image conversion utilities
- **`backend/DobotDllType.py`**: Dobot SDK wrapper

---

## 📊 Data Flow

```
Image Data Flow:
DroidCam → MJPEG Stream → Backend Extraction → JPEG Blob → Frontend → FormData → Backend → PIL Image → YOLO Model → Prediction

Robot Control Flow:
Prediction → Class Name → Bin Position Lookup → Dobot SDK → Robot Movement → Success/Error
```

---

## ⚙️ Configuration

### Model Path
- **Expected**: `backend/models/best.pt`
- **Training Output**: `training/model_output/run/weights/best.pt`
- **Note**: Model needs to be copied or symlinked to expected location

### Bin Positions
Defined in `backend/services/dobot_service.py`:
```python
BIN_POSITIONS = {
    "plastic": (250, 0, -40, 0),
    "metal": (200, 100, -40, 0),
    "paper": (200, -100, -40, 0),
    # ... etc
}
```

### Robot Positions
- **PICKUP_POSITION**: Where items are placed for sorting
- **HOME_POSITION**: Safe starting position
- **Movement Parameters**: Speed, acceleration, height offsets

---

## ⚠️ Current Limitations

1. **No Confidence Threshold**: Robot sorts even with low confidence predictions
2. **Automatic Sorting**: No manual confirmation before robot action
3. **Blocking Operations**: Robot movements block API response (synchronous)
4. **Model Path Mismatch**: Training saves to different location than expected
5. **No Error Recovery**: If robot fails mid-sequence, no automatic retry

---

## 🔄 Alternative Workflows

### Manual Mode (Not Yet Implemented)
- User captures frame
- ML prediction displayed
- User reviews prediction
- User manually triggers robot action

### Auto Mode (Current Implementation)
- User captures frame
- ML prediction triggers automatic robot sorting
- Results displayed after completion

---

*Last Updated: Based on current codebase analysis*



