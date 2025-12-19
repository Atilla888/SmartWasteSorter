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

```
1. User clicks "Capture & Send"
   ↓
2. Frontend pauses MJPEG preview (releases DroidCam connection)
   ↓
3. Backend extracts single JPEG frame from DroidCam stream
   ↓
4. Frontend uploads frame to backend
   ↓
5. Backend saves frame and runs ML inference (YOLOv8)
   ↓
6. Backend triggers robot sorting based on prediction
   ↓
7. Robot executes 9-step sorting sequence:
   - Move to pickup position
   - Descend and close gripper
   - Lift item
   - Move to appropriate bin
   - Descend and open gripper
   - Return home
   ↓
8. Results returned to frontend and displayed
   ↓
9. Preview resumes automatically
```

### Detailed Step-by-Step

**Phase 1: Image Capture**
1. User clicks "Capture & Send" button
2. Frontend pauses MJPEG preview stream
3. 250ms delay to allow DroidCam to free the connection
4. Backend connects to DroidCam MJPEG stream (`http://{ip}:4747/video`)
5. Backend extracts first JPEG frame (finds SOI/EOI markers)
6. JPEG blob returned to frontend

**Phase 2: Image Processing & ML Inference**
1. Frontend creates FormData with captured image
2. POST request to `/api/capture` endpoint
3. Backend decodes image (PIL Image, RGB format)
4. Image saved to `backend/frames/` with timestamp filename
5. YOLOv8 model loaded (cached after first load)
6. Model inference runs on image
7. Top-1 prediction and confidence extracted

**Phase 3: Robot Sorting**
1. Prediction class name mapped to bin position
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

**Phase 4: Response**
1. Backend builds JSON response with:
   - Success status
   - Saved filename
   - Prediction class
   - Confidence score
   - Robot action status
2. Frontend displays results
3. Preview stream resumes

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
cd my-sortingwaste-project
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

**Important**: Ensure the Dobot SDK files are in `backend/dobot_magician/`:
- `DobotDll.dll`
- `DobotDllType.py`
- Supporting DLLs (msvcp120.dll, msvcr120.dll, Qt5*.dll)

#### 3. Frontend Setup

```bash
# From project root
npm install
```

#### 4. ML Model

Place your trained YOLOv8 model at:
```
backend/models/best.pt
```

If training a new model, see `training/README.md`.

### Running the Application

#### Start Backend

From project root:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or from `backend/` directory:
```bash
python main.py
```

Backend will be available at: `http://localhost:8000`

#### Start Frontend

From project root:
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
5. Watch the robot sort the item!

---

## Project Structure

```
my-sortingwaste-project/
├── app/                          # Next.js App Router
│   ├── api/                      # API routes (proxies to FastAPI)
│   │   ├── capture/route.ts     # Image upload proxy
│   │   └── snapshot/route.ts    # Frame extraction proxy
│   ├── page.tsx                  # Main page
│   └── layout.tsx
│
├── components/                    # React components
│   ├── sorter/
│   │   └── CameraFeed.tsx        # MJPEG preview component
│   └── ui/                       # shadcn/ui components
│       └── demo.tsx              # Main control panel
│
├── lib/
│   └── sorter/
│       └── capture.ts            # Frame capture utility
│
├── backend/                       # FastAPI backend
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt          # Python dependencies
│   │
│   ├── services/
│   │   ├── camera_service.py     # ML inference & image processing
│   │   ├── snapshot_service.py   # DroidCam frame extraction
│   │   ├── dobot_service.py      # Robot control
│   │   └── COORDINATE_ADJUSTMENT_GUIDE.md  # Calibration guide
│   │
│   ├── utils/
│   │   └── image_utils.py        # Image conversion utilities
│   │
│   ├── models/
│   │   └── best.pt               # YOLOv8 model (place here)
│   │
│   ├── frames/                    # Saved captured frames
│   │
│   ├── dobot_magician/           # Dobot SDK files
│   │   ├── DobotDll.dll
│   │   ├── DobotDllType.py
│   │   └── README.md              # SDK documentation
│   │
│   └── README.md                 # Backend-specific documentation
│
├── training/                      # ML model training
│   ├── train.py                  # Training script
│   ├── train.ipynb               # Jupyter notebook
│   └── README.md                 # Training guide
│
└── README.md                      # This file
```

---

## Known Limitations

### Current Limitations

1. **No Confidence Threshold**: Robot sorts items even with low confidence predictions
2. **Automatic Sorting**: No manual confirmation before robot action
3. **Blocking Operations**: Robot movements block API response (synchronous)
4. **Model Path**: Training saves to `training/model_output/run/weights/best.pt`, but application expects `backend/models/best.pt` (manual copy required)
5. **No Error Recovery**: If robot fails mid-sequence, no automatic retry mechanism
6. **Single Camera Connection**: DroidCam Free only allows one connection at a time (preview must pause for capture)
7. **Windows Only**: Dobot SDK requires Windows OS
8. **Coordinate Calibration Required**: Bin positions must be manually calibrated for each physical setup

### Technical Constraints

- **DroidCam Free Limitation**: Only one connection to `/video` stream at a time
- **USB Connection**: Dobot must be connected via USB (COM port)
- **Synchronous Robot Control**: All movements are blocking (wait for completion)
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

- **Backend Details**: See `backend/README.md` for API endpoints, services, and environment variables
- **Training Guide**: See `training/README.md` for ML model training instructions
- **Coordinate Calibration**: See `backend/services/COORDINATE_ADJUSTMENT_GUIDE.md` for robot position setup
- **Dobot SDK**: See `backend/dobot_magician/README.md` for SDK documentation

---

## License

This project is part of a university course (Applied Robotics / Computer Vision).

---

*Last Updated: Based on current codebase analysis*
