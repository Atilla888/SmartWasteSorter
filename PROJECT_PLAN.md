# Smart Waste Sorter - Complete Project Plan

## 📋 Project Overview

A full-stack robotic application that uses computer vision and machine learning to automatically sort waste items using a Dobot Magician robot arm. The system connects to a DroidCam video stream, performs real-time waste classification, and controls the robot arm to sort items into appropriate bins.

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│   Next.js UI    │  ← Frontend (React/TypeScript)
│  (Control Panel)│
└────────┬────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────┐
│   FastAPI       │  ← Backend API (Python)
│   (REST/WS)     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│  ML    │ │  Dobot       │
│ Model  │ │  Controller  │
└────────┘ └──────────────┘
    │            │
    ▼            ▼
┌─────────────────────────┐
│   DroidCam Stream       │
│   (Phone Camera)        │
└─────────────────────────┘
```

---

## 📁 Project Structure

```
my-sortingwaste-project/
├── app/                          # Next.js App Router
│   ├── api/                      # Next.js API routes (proxy to FastAPI)
│   │   ├── camera/
│   │   │   └── route.ts         # Camera connection endpoints
│   │   ├── predict/
│   │   │   └── route.ts         # ML prediction proxy
│   │   └── robot/
│   │       └── route.ts         # Robot control proxy
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
│
├── components/
│   ├── ui/                       # shadcn components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── demo.tsx
│   │   └── ...
│   ├── camera/
│   │   ├── CameraView.tsx       # Video stream display
│   │   └── CameraControls.tsx   # Camera connection controls
│   ├── control-panel/
│   │   ├── ControlPanel.tsx     # Main control panel
│   │   ├── StatusDisplay.tsx    # System status
│   │   └── RobotControls.tsx    # Manual robot controls
│   └── prediction/
│       └── PredictionDisplay.tsx # ML prediction results
│
├── lib/
│   ├── utils.ts
│   ├── api-client.ts             # API client for FastAPI
│   └── websocket-client.ts       # WebSocket client
│
├── hooks/
│   ├── useCamera.ts              # Camera connection hook
│   ├── usePrediction.ts          # ML prediction hook
│   └── useRobot.ts               # Robot control hook
│
├── types/
│   └── index.ts                  # TypeScript type definitions
│
├── backend/                      # FastAPI Backend (Python)
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── camera.py         # Camera endpoints
│   │   │   ├── predict.py         # ML prediction endpoints
│   │   │   └── robot.py           # Robot control endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py          # Configuration
│   │   │   └── websocket.py       # WebSocket handlers
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── camera_service.py  # DroidCam connection
│   │   │   ├── ml_service.py      # ML model inference
│   │   │   └── robot_service.py   # Dobot control
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── prediction.py      # Pydantic models
│   │       └── robot.py
│   └── ml/
│       ├── __init__.py
│       ├── model_loader.py        # Load ML model
│       ├── preprocessor.py        # Image preprocessing
│       └── classifier.py          # Waste classification
│
└── robot/                        # Dobot Robot Control
    ├── __init__.py
    ├── dobot_controller.py       # Dobot SDK wrapper
    ├── movements.py              # Predefined movements
    └── calibration.py            # Robot calibration
```

---

## 🎨 Frontend Components

### 1. **Control Panel** (`components/control-panel/ControlPanel.tsx`)
- Main control interface
- Buttons: Connect Camera, Start Auto Mode, Manual Mode, Emergency Stop
- Status indicators (camera, robot, ML model)
- Real-time feedback

### 2. **Camera View** (`components/camera/CameraView.tsx`)
- Displays DroidCam video stream
- Frame capture button
- Stream status indicator
- Video quality controls

### 3. **Camera Controls** (`components/camera/CameraControls.tsx`)
- DroidCam IP/port configuration
- Connection/disconnection controls
- Stream quality settings

### 4. **Status Display** (`components/control-panel/StatusDisplay.tsx`)
- System status (camera, robot, ML model)
- Connection indicators
- Error messages
- Statistics (items sorted, accuracy)

### 5. **Robot Controls** (`components/control-panel/RobotControls.tsx`)
- Manual movement controls (X, Y, Z, rotation)
- Predefined positions (home, pickup, drop zones)
- Speed controls
- Gripper open/close

### 6. **Prediction Display** (`components/prediction/PredictionDisplay.tsx`)
- Shows ML prediction results
- Confidence scores
- Visual feedback (bounding boxes if available)
- Classification history

---

## 🔌 Backend API Routes (FastAPI)

### Camera Endpoints (`/api/camera`)
- `POST /api/camera/connect` - Connect to DroidCam
- `GET /api/camera/stream` - Get video stream (MJPEG/WebSocket)
- `POST /api/camera/capture` - Capture single frame
- `POST /api/camera/disconnect` - Disconnect camera
- `GET /api/camera/status` - Get camera connection status

### ML Prediction Endpoints (`/api/predict`)
- `POST /api/predict/image` - Predict waste type from image
- `POST /api/predict/stream` - Real-time prediction from stream
- `GET /api/predict/model/status` - Check ML model status
- `POST /api/predict/model/reload` - Reload ML model

### Robot Control Endpoints (`/api/robot`)
- `POST /api/robot/connect` - Connect to Dobot
- `POST /api/robot/disconnect` - Disconnect from Dobot
- `POST /api/robot/move` - Move robot to position
- `POST /api/robot/pick` - Pick item at position
- `POST /api/robot/place` - Place item at position
- `POST /api/robot/home` - Move to home position
- `POST /api/robot/emergency_stop` - Emergency stop
- `GET /api/robot/status` - Get robot status
- `GET /api/robot/position` - Get current position

### WebSocket Endpoints (`/ws`)
- `/ws/camera` - Real-time camera stream
- `/ws/predictions` - Real-time prediction updates
- `/ws/robot` - Robot status updates

---

## 🐍 Python Backend Services

### 1. **Camera Service** (`services/camera_service.py`)
```python
class CameraService:
    - connect_droidcam(ip: str, port: int) -> bool
    - get_stream() -> Generator[bytes]
    - capture_frame() -> np.ndarray
    - disconnect() -> None
    - is_connected() -> bool
```

**DroidCam Integration:**
- Connect via HTTP to DroidCam server (default: `http://192.168.x.x:4747`)
- Stream MJPEG video feed
- Capture frames for ML processing
- Handle reconnection logic

### 2. **ML Service** (`services/ml_service.py`)
```python
class MLService:
    - load_model(model_path: str) -> None
    - predict(image: np.ndarray) -> PredictionResult
    - preprocess(image: np.ndarray) -> np.ndarray
    - get_model_info() -> dict
```

**ML Model Requirements:**
- Input: RGB image (224x224 or 640x640)
- Output: Classification (plastic, paper, glass, metal, organic, etc.)
- Confidence scores for each class
- Model format: PyTorch (.pth) or TensorFlow (.h5) or ONNX (.onnx)

**Recommended Models:**
- Custom trained CNN
- Transfer learning (ResNet, EfficientNet)
- YOLO for object detection + classification

### 3. **Robot Service** (`services/robot_service.py`)
```python
class RobotService:
    - connect(port: str) -> bool
    - move_to(x, y, z, r) -> bool
    - pick_item(x, y, z) -> bool
    - place_item(x, y, z, waste_type: str) -> bool
    - home() -> bool
    - emergency_stop() -> None
    - get_position() -> tuple
    - disconnect() -> None
```

**Dobot Magician Integration:**
- Use `pydobot` library (Python SDK)
- Serial/USB connection
- Coordinate system calibration
- Predefined positions for bins (plastic, paper, glass, etc.)
- Gripper control (open/close)

---

## 🤖 Robot Control Logic

### Movement Sequence:
1. **Home Position** → Move to safe starting position
2. **Pickup Zone** → Move above item
3. **Descend** → Lower to item height
4. **Grip** → Close gripper
5. **Ascend** → Lift item
6. **Bin Position** → Move to appropriate bin based on classification
7. **Descend** → Lower to bin
8. **Release** → Open gripper
9. **Return Home** → Move back to home position

### Bin Positions (Calibrated):
- **Plastic**: (x1, y1, z1)
- **Paper**: (x2, y2, z2)
- **Glass**: (x3, y3, z3)
- **Metal**: (x4, y4, z4)
- **Organic**: (x5, y5, z5)
- **Other**: (x6, y6, z6)

---

## 🔄 Integration Pipeline

### Full Automatic Mode Flow:
```
1. User clicks "Start Auto Mode"
   ↓
2. Frontend → Backend: POST /api/camera/connect
   ↓
3. Backend connects to DroidCam
   ↓
4. Frontend → Backend: POST /api/robot/connect
   ↓
5. Backend connects to Dobot
   ↓
6. Loop:
   a. Backend captures frame from DroidCam
   b. Backend → ML Service: predict(frame)
   c. ML Service returns: {class: "plastic", confidence: 0.95}
   d. Backend → Robot Service: pick_item(x, y, z)
   e. Robot Service: place_item(bin_position[class])
   f. Backend → Frontend: WebSocket update
   g. Frontend displays result
   ↓
7. Continue until stopped
```

### Manual Mode Flow:
```
1. User clicks "Manual Mode"
   ↓
2. User captures frame manually
   ↓
3. Frontend → Backend: POST /api/predict/image
   ↓
4. Backend returns prediction
   ↓
5. User reviews prediction
   ↓
6. User clicks "Execute" or manually controls robot
   ↓
7. Frontend → Backend: POST /api/robot/move or /api/robot/pick
```

---

## 📦 Dependencies

### Frontend (package.json):
```json
{
  "dependencies": {
    "next": "^16.0.3",
    "react": "^19.2.0",
    "typescript": "^5",
    "tailwindcss": "^4",
    "@splinetool/react-spline": "^4.1.0",
    "lucide-react": "^0.553.0",
    "zustand": "^4.x",  // State management
    "axios": "^1.x",    // HTTP client
    "socket.io-client": "^4.x"  // WebSocket client
  }
}
```

### Backend (requirements.txt):
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
opencv-python==4.8.1
numpy==1.24.3
pillow==10.1.0
pydobot==1.0.0  # Dobot SDK
torch==2.1.0  # or tensorflow==2.15.0
torchvision==0.16.0
pydantic==2.5.0
websockets==12.0
aiofiles==23.2.1
python-dotenv==1.0.0
```

---

## 🔐 State Management

### Frontend State (Zustand):
```typescript
interface AppState {
  // Camera
  cameraConnected: boolean
  cameraStreaming: boolean
  cameraUrl: string
  
  // ML
  modelLoaded: boolean
  lastPrediction: PredictionResult | null
  
  // Robot
  robotConnected: boolean
  robotPosition: Position
  robotStatus: 'idle' | 'moving' | 'picking' | 'placing' | 'error'
  
  // System
  mode: 'manual' | 'auto' | 'off'
  error: string | null
}
```

---

## 🌐 DroidCam Streaming

### Connection Method:
1. **DroidCam App** running on phone
2. **DroidCam Server** running on phone (default port: 4747)
3. **Backend connects** via HTTP: `http://<phone_ip>:4747/video`
4. **Stream format**: MJPEG (Motion JPEG)
5. **Backend processes** frames using OpenCV

### Implementation:
```python
import cv2

def connect_droidcam(ip: str, port: int = 4747):
    url = f"http://{ip}:{port}/video"
    cap = cv2.VideoCapture(url)
    return cap

def get_frame(cap):
    ret, frame = cap.read()
    return frame if ret else None
```

---

## 🚀 Development Phases

### Phase 1: ✅ UI Foundation (Current)
- [x] Next.js setup
- [x] Spline 3D scene
- [x] Basic UI components
- [x] Control Panel with buttons

### Phase 2: Camera Integration
- [x] DroidCam connection UI
- [x] Video stream display
- [x] Frame capture functionality
- [ ] Backend camera service

### Phase 3: ML Integration
- [ ] ML model selection/loading
- [ ] Image preprocessing
- [ ] Prediction API
- [ ] Results display

### Phase 4: Robot Integration
- [ ] Dobot connection
- [ ] Basic movement controls
- [ ] Pick and place logic
- [ ] Calibration system

### Phase 5: Full Integration
- [ ] Automatic mode pipeline
- [ ] Error handling
- [ ] Safety features
- [ ] Performance optimization

### Phase 6: Polish
- [ ] UI/UX improvements
- [ ] Logging and monitoring
- [ ] Documentation
- [ ] Testing

---

## 🔧 Configuration

### Environment Variables (.env):
```env
# Backend
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Camera
DROIDCAM_DEFAULT_IP=192.168.1.100
DROIDCAM_DEFAULT_PORT=4747

# Robot
DOBOT_PORT=COM3  # Windows: COM3, Linux: /dev/ttyUSB0
DOBOT_BAUDRATE=115200

# ML Model
ML_MODEL_PATH=./models/waste_classifier.pth
ML_MODEL_TYPE=pytorch  # pytorch, tensorflow, onnx
ML_INPUT_SIZE=224

# Bin Positions (calibrated)
BIN_PLASTIC_X=100
BIN_PLASTIC_Y=200
BIN_PLASTIC_Z=50
# ... (other bins)
```

---

## 📝 API Request/Response Examples

### Connect Camera:
```typescript
POST /api/camera/connect
Body: { ip: "192.168.1.100", port: 4747 }
Response: { success: true, message: "Connected" }
```

### Predict Image:
```typescript
POST /api/predict/image
Body: FormData { image: File }
Response: {
  class: "plastic",
  confidence: 0.95,
  all_classes: [
    { name: "plastic", score: 0.95 },
    { name: "paper", score: 0.03 },
    ...
  ]
}
```

### Move Robot:
```typescript
POST /api/robot/move
Body: { x: 100, y: 200, z: 50, r: 0 }
Response: { success: true, position: { x: 100, y: 200, z: 50, r: 0 } }
```

---

## 🎯 Next Steps

1. ✅ Create project plan (this document)
2. ✅ Add Control Panel UI with "Connect Camera" button
3. ✅Implement camera connection logic
4. Set up FastAPI backend structure
5. Implement DroidCam service
6. Integrate ML model
7. Connect Dobot robot
8. Build full pipeline

---

## 📚 Resources

- **DroidCam**: https://www.dev47apps.com/
- **Dobot Magician**: https://www.dobot.cc/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Next.js Docs**: https://nextjs.org/docs
- **shadcn/ui**: https://ui.shadcn.com/

---

*Last Updated: [14.11.2025]*

