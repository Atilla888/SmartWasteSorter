# Smart Waste Sorter

A full-stack robotic application that uses computer vision and machine learning to automatically sort waste items using a Dobot Magician robot arm. The system connects to a DroidCam video stream, performs real-time waste classification, and controls the robot arm to sort items into appropriate bins.

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Application Workflow](#application-workflow)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Known Limitations](#known-limitations)

---

## Overview

The Smart Waste Sorter is an automated waste sorting system that combines:

- **Computer Vision**: Real-time camera feed from DroidCam (phone camera)
- **Machine Learning**: YOLOv8 classification model for waste type detection
- **Robotics**: Dobot Magician robotic arm for automated sorting
- **Full-Stack Web Application**: Next.js frontend with FastAPI backend

### What It Does

1. Captures images from a DroidCam video stream
2. Classifies waste items using a trained YOLOv8 model (12 waste categories)
3. Automatically controls a Dobot Magician robot arm to sort items into appropriate bins
4. Provides real-time feedback through a web interface

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  User Interface                                      │   │
│  │  - Camera preview (MJPEG stream)                     │   │
│  │  - "Capture & Send" button                           │   │
│  │  - Prediction results display                        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP API
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI - Python)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Snapshot    │  │  Camera      │  │  Dobot       │       │
│  │  Service     │  │  Service     │  │  Service     │       │
│  │  (Frame      │  │  (ML         │  │  (Robot      │       │
│  │  Extraction) │  │  Inference)  │  │  Control)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────┬──────────────────┬──────────────────┬──────────┘
             │                  │                  │
             ▼                  ▼                  ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  DroidCam    │  │  YOLOv8      │  │  Dobot       │
    │  (Phone      │  │  Model       │  │  Magician    │
    │  Camera)     │  │  (best.pt)   │  │  (USB)       │
    └──────────────┘  └──────────────┘  └──────────────┘
```

### Components

**Frontend (Next.js)**
- React-based web interface
- Real-time MJPEG camera preview
- Image capture and upload
- Results display

**Backend (FastAPI)**
- **Snapshot Service**: Extracts frames from DroidCam MJPEG stream
- **Camera Service**: Processes images, runs ML inference
- **Dobot Service**: Controls robot arm movements and sorting

**External Systems**
- **DroidCam**: Phone camera streaming via WiFi (MJPEG)
- **YOLOv8 Model**: Pre-trained classification model
- **Dobot Magician**: Robotic arm with gripper end effector

---

## Application Workflow

### End-to-End Pipeline


### Detailed Step-by-Step

**Phase 1: Image Capture**
1. User clicks "Capture & Send" button
2. Frontend validates camera is connected and IP address is provided
3. Frontend shows status: "Pausing preview..."
4. Frontend pauses MJPEG preview stream (sets `previewPaused = true`)
5. 250ms delay to allow DroidCam to free the connection
6. Frontend shows status: "Capturing frame from camera..."
7. Frontend calls `/api/snapshot?ip={ip}` endpoint
8. Backend connects to DroidCam MJPEG stream (`http://{ip}:4747/video`)
9. Backend extracts first JPEG frame (finds SOI/EOI markers)
10. Backend returns JPEG blob with enhanced error handling:
    - Invalid IP: Clear error message with format example
    - Connection errors: Troubleshooting hints (check camera, network, app)
    - Timeout errors: Suggests camera may be busy
    - Stream errors: Indicates corrupted stream

**Phase 2: Image Processing & ML Inference**
1. Frontend shows status: "Uploading image to server..."
2. Frontend creates FormData with captured image blob
3. Frontend shows status: "Processing image..."
4. POST request to `/api/capture` endpoint
5. **Backend validation steps:**
   - Validates file size (default max: 10MB, configurable via `MAX_FILE_SIZE` env var)
   - Validates file is not empty
   - Returns clear error if file too large or empty
6. Backend decodes image (PIL Image, RGB format) with error handling:
   - Returns user-friendly error if image format is invalid
7. Backend sanitizes filename:
   - Removes directory traversal attempts
   - Removes invalid filesystem characters
   - Limits filename length to 255 characters
8. Image saved to `backend/frames/` with sanitized timestamp filename
9. Frontend shows status: "Running ML inference..."
10. YOLOv8 model loaded (cached after first load, lazy loading)
11. Model inference runs on image with enhanced error handling:
    - FileNotFoundError: Clear message if model missing
    - RuntimeError: Indicates model corruption or incompatibility
12. Top-1 prediction and confidence extracted

**Phase 3: Robot Sorting**
1. Prediction class name mapped to bin position (paper, plastic, glass, biological, trash)
2. Dobot service auto-connects if needed
3. Robot executes sorting sequence:
   - Move above pickup position
   - Descend to pickup height
   - Close gripper (pick item)
   - Lift item
   - Move above target bin
   - Descend to bin height
   - Open gripper (place item)
   - Lift up
   - Return to home position
4. Robot operation status captured (success or error message)

**Phase 4: Response & Display**
1. Backend builds JSON response with:
   - Success status
   - Saved filename
   - Prediction class
   - Confidence score (0.0-1.0)
   - Robot action status (includes error message if robot failed)
2. Frontend receives response and formats display:
   - Success: "Image processed successfully! Saved as: {filename} | Prediction: {class} ({confidence}%) | Robot: {status}"
   - Error: "Processing failed: {error} | Tip: {troubleshooting_hint}"
3. Error messages include context-specific troubleshooting hints:
   - File size errors: Suggests using smaller image
   - Image format errors: Suggests valid formats
   - Model errors: Suggests checking model configuration
   - Disk errors: Suggests checking space and permissions
4. Preview stream resumes automatically (`previewPaused = false`)

---

## Tech Stack

### Frontend
- **Next.js 16.3** (React framework)
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui** components

### Backend
- **FastAPI** (Python web framework)
- **Uvicorn** (ASGI server)
- **Pillow** (Image processing)
- **Ultralytics YOLOv8** (ML model)
- **httpx** (Async HTTP client)

### ML/AI
- **YOLOv8** classification model
- **PyTorch** (via Ultralytics)
- 12 waste categories: battery, biological, brown-glass, cardboard, clothes, green-glass, metal, paper, plastic, shoes, trash, white-glass

### Robotics
- **Dobot Magician** robotic arm
- **Dobot SDK** (Windows DLL + Python wrapper)
- USB/Serial connection

### Camera
- **DroidCam** (phone camera streaming)
- MJPEG stream over WiFi

---

## Getting Started

### Prerequisites

- **Python 3.10+** (64-bit on Windows)
- **Node.js 18+** and npm
- **Dobot Magician** robot arm (connected via USB)
- **DroidCam** app installed on phone
- **Windows OS** (required for Dobot SDK)

### Installation

#### 1. Clone and Navigate

```bash
cd <your-project-directory>
```

#### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

#### 3. Dobot SDK Setup

**Important**: The official Dobot Magician SDK requires modifications to work correctly with this project. The SDK files are **not included** in this repository.

**Step 1: Download Official SDK**
1. Download the official Dobot Magician Python SDK from the Dobot website
2. Extract the SDK files to a temporary location

**Step 2: Copy SDK Files**
Copy the following files from the official SDK to `backend/dobot_magician/`:
- `DobotDll.dll` (Windows 64-bit)
- `DobotDllType.py`
- `DobotControl.py`
- Supporting DLLs: `msvcp120.dll`, `msvcr120.dll`, `Qt5Core.dll`, `Qt5Network.dll`, `Qt5SerialPort.dll`

**Step 3: Modify `DobotDllType.py`**

The official SDK's `load()` function uses relative paths that fail when the script is run from different directories. You must modify `backend/dobot_magician/DobotDllType.py`:

**Why changes are needed:**
- The original SDK uses `"./DobotDll.dll"` (relative path), which only works when running from the SDK directory
- The original uses `CDLL` with `RTLD_GLOBAL` flag, which is Linux/Mac-specific and causes issues on Windows
- The project needs to load the DLL from any working directory

**Required modifications:**

1. **Add import at the top** (after line 3, with other imports):
   ```python
   from pathlib import Path
   ```

2. **Replace the `load()` function** (around line 587-595) with:
   ```python
   def load():
       dll_path = str(Path(__file__).resolve().parent / "DobotDll.dll")
       print("Loading Dobot DLL from:", dll_path)
       if platform.system() == "Windows":
           print("您用的dll是64位，为了顺利运行，请保证您的python环境也是64位")
           print("python环境是：",platform.architecture())
           from ctypes import WinDLL
           return WinDLL(dll_path)
       elif platform.system() == "Darwin":
           dylib_path = str(Path(__file__).resolve().parent / "libDobotDll.dylib")
           return CDLL(dylib_path)
       elif platform.system() == "Linux":
           return CDLL("libDobotDll.so")
   ```

**What changed:**
- **Absolute path resolution**: Uses `Path(__file__).resolve().parent` to find the DLL relative to the script's location, regardless of working directory
- **Windows-specific loading**: Uses `WinDLL` instead of `CDLL` on Windows (more appropriate for Windows DLLs)
- **Removed RTLD_GLOBAL**: This flag is Linux/Mac-specific and not needed on Windows
- **macOS path fix**: Also uses absolute path for macOS dylib

**Verification:**
After making these changes, the SDK should load correctly when running the backend from any directory.

#### 3. Frontend Setup

```bash
# From project root
cd frontend
npm install
```

**Note:** All Next.js commands should be run from within this directory.

#### 4. ML Model

Place your trained YOLOv8 model at:
```
backend/models/best.pt
```

Or use existing model located at backend/models/best.pt

### Running the Application

#### Start Backend

**Important:** The backend now validates environment variables on startup. Optional variables will show warnings, but the server will start with defaults.

From project root:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or from `backend/` directory:
```bash
python main.py
```

**Environment Variables (Optional):**
- `YOLO_MODEL_PATH`: Path to YOLO model file (defaults to `backend/models/best.pt`)
- `YOLO_DEVICE`: Device for inference: `cpu` or `cuda` (defaults to `cpu`)
- `MAX_FILE_SIZE`: Maximum file size in bytes (defaults to 10MB = 10485760)
- `FASTAPI_URL`: Backend URL for frontend (defaults to `http://localhost:8000`)

The backend will validate these on startup and show warnings if using defaults.

Backend will be available at: `http://localhost:8000`

#### Start Frontend

From project root:
```bash
cd frontend
npm run dev
```

Or from `frontend/` directory:
```bash
npm run dev
```

Frontend will be available at: `http://localhost:3000`

#### Connect DroidCam

1. Start DroidCam app on your phone
2. Note the IP address (e.g., `192.168.0.105`)
3. Ensure phone and computer are on the same WiFi network
4. In the web interface, enter the IP and click "Connect Camera"

#### Test the System

1. Open `http://localhost:3000`
2. Enter DroidCam IP and connect
3. Place a waste item in the pickup area
4. Click "Capture & Send"
5. Watch the robot sort the item


## Project Structure

```
your-project-directory/
├── frontend/                       # Next.js frontend application
│   ├── app/                       # Next.js App Router
│   │   ├── api/                   # API routes (proxies to FastAPI)
│   │   │   ├── capture/route.ts  # Image upload proxy
│   │   │   └── snapshot/route.ts # Frame extraction proxy
│   │   ├── page.tsx               # Main page
│   │   └── layout.tsx
│   │
│   ├── components/                 # React components
│   │   ├── sorter/
│   │   │   └── CameraFeed.tsx     # MJPEG preview component
│   │   └── ui/                    # shadcn/ui components
│   │       └── demo.tsx           # Main control panel
│   │
│   ├── lib/
│   │   └── sorter/
│   │       └── capture.ts         # Frame capture utility
│   │
│   ├── public/                     # Static assets
│   ├── package.json               # Frontend dependencies
│   ├── next.config.ts             # Next.js configuration
│   └── tsconfig.json              # TypeScript configuration
│
├── backend/                        # FastAPI backend
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt           # Python dependencies
│   │
│   ├── services/
│   │   ├── camera_service.py      # ML inference & image processing
│   │   ├── snapshot_service.py    # DroidCam frame extraction
│   │   ├── dobot_service.py       # Robot control
│   │   └── COORDINATE_ADJUSTMENT_GUIDE.md  # Calibration guide
│   │
│   ├── models/
│   │   ├── best.onnx              # YOLOv8 model .onnx
│   │   └── best.pt                # YOLOv8 model .pt (place here)
│   │
│   ├── utils/
│   │   └── image_utils.py         # Image conversion utilities
│   │
│   ├── frames/                    # Saved captured frames
│   │
│   ├── dobot_magician/            # Dobot SDK files (place here)
│   │   ├── DobotDll.dll
│   │   ├── DobotDllType.py
│   │   ├── DobotControl.py
│   │   └── ...                    # remaining SDK files
│   │
│   └── BACKEND.md                 # Backend-specific documentation
│
├── docs/                          # Additional documentation
├── training/                      # ML model training data and scripts
└── README.md                      # This file
```

---

## Known Limitations

### Current Limitations

1. **No Confidence Threshold**: Robot sorts items even with low confidence predictions
2. **Automatic Sorting**: No manual confirmation before robot action
3. **Blocking Operations**: Robot movements block API response (synchronous)
4. **No Error Recovery**: If robot fails mid-sequence, no automatic retry mechanism
5. **Single Camera Connection**: DroidCam Free only allows one connection at a time (preview must pause for capture)
6. **Windows Only**: Dobot SDK requires Windows OS
7. **Coordinate Calibration Required**: Bin positions must be manually calibrated for each physical setup

### Recent Enhancements [29.12.2025]

The following improvements have been implemented:

1. **File Size Validation**: Images larger than 10MB are rejected with clear error messages
2. **Environment Variable Validation**: Backend validates configuration on startup with helpful warnings
3. **Progress Indicators**: Real-time status updates during processing ("Pausing preview...", "Capturing frame...", "Processing image...", "Running ML inference...")
4. **Enhanced Error Messages**: All errors include context-specific troubleshooting hints and user-friendly descriptions
5. **Filename Sanitization**: All saved filenames are sanitized to prevent security issues (directory traversal, invalid characters)
6. **Better Error Handling**: Comprehensive error handling at each processing stage with specific error messages

### Technical Constraints

- **DroidCam Free Limitation**: Only one connection to `/video` stream at a time
- **USB Connection**: Dobot must be connected via USB (COM port)
- **No Real-time Streaming**: ML inference runs on-demand, not continuously

### Future Improvements

- Add confidence threshold before robot action
- Implement manual confirmation mode
- Add error recovery and retry logic
- Support for multiple camera streams
- Asynchronous robot control with status updates
- Real-time prediction streaming
- Cross-platform Dobot SDK support

---

## Additional Documentation

- **Backend Details**: See `backend/BACKEND.md` for API endpoints, services, and environment variables, robot position setup
- **Dobot SDK**: See `https://www.dobot-robots.com/service/download-center` for SDK documentation and files

**Note:** ML model training instructions are not included in this repository. To train a YOLOv8 classification model, refer to the Ultralytics documentation and organize your dataset in class subfolders.

## Error Handling & Troubleshooting

The application now includes comprehensive error handling with user-friendly messages:

- **File Size Errors**: Clear messages when files exceed 10MB limit, with suggestions to use smaller images
- **Image Format Errors**: Helpful messages when invalid image formats are uploaded
- **Camera Connection Errors**: Troubleshooting hints for DroidCam connection issues (check power, IP, network, app status)
- **ML Model Errors**: Clear messages if model is missing or corrupted
- **Robot Errors**: Robot operation status included in response even if robot fails (ML prediction still returned)
- **Network Errors**: Timeout and connection error messages with retry suggestions

All error messages include context-specific troubleshooting tips to help users resolve issues independently.

---

This project is part of a university course (Applied Robotics).

---
