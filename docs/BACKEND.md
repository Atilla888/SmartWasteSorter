# Backend Documentation

FastAPI backend for the Smart Waste Sorter application.

## Overview

The backend provides REST API endpoints for:
- Frame extraction from DroidCam streams
- Image processing and ML inference
- Robot control and sorting operations

## API Endpoints

### Health Check

**GET** `/`
- Returns: `{"message": "Smart Waste Sorter API is running"}`

### Snapshot (Frame Extraction)

**GET** `/snapshot?ip={ip}`

Extracts a single JPEG frame from DroidCam MJPEG stream.

**Query Parameters:**
- `ip` (required): DroidCam IP address (e.g., `192.168.0.105`)

**Response:**
- Content-Type: `image/jpeg`
- Body: JPEG image bytes

**Example:**
```bash
curl "http://localhost:8000/snapshot?ip=192.168.0.105" --output frame.jpg
```

**Error Responses:**
- `400`: Invalid IP address or connection error
- `503`: DroidCam unavailable or timeout
- `500`: Unexpected error

### Capture (Image Processing & ML Inference)

**POST** `/capture`

Processes an uploaded image: saves to disk, runs ML inference, and triggers robot sorting.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file: <image blob>`

**Response:**
```json
{
  "success": true,
  "saved_as": "frame_20241121_143022_456.jpg",
  "prediction": "plastic",
  "confidence": 0.95,
  "robot_action": "Sorted to PLASTIC bin"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/capture" \
  -F "file=@/path/to/image.jpg"
```

---

## Services

### Snapshot Service (`services/snapshot_service.py`)

**Function:** `extract_single_frame(ip: str) -> bytes`

Connects to DroidCam MJPEG stream and extracts the first JPEG frame.

**How it works:**
1. Connects to `http://{ip}:4747/video` (MJPEG stream)
2. Reads stream data until JPEG markers found:
   - `b'\xff\xd8'` (Start of Image - SOI)
   - `b'\xff\xd9'` (End of Image - EOI)
3. Returns complete JPEG frame as bytes

**Dependencies:**
- `httpx` for async HTTP streaming

### Camera Service (`services/camera_service.py`)

**Function:** `process_frame(file: UploadFile) -> dict`

Processes uploaded images and runs ML inference.

**Workflow:**
1. Decodes uploaded file to PIL Image (RGB)
2. Saves image to `backend/frames/` with timestamp filename
3. Loads YOLOv8 model (cached after first load)
4. Runs inference on image
5. Extracts top-1 prediction and confidence
6. Triggers robot sorting via `dobot_service.sort_with_robot()`
7. Returns results

**Model Configuration:**
- Default Path: `backend/models/best.pt`
- Environment Override: Set `YOLO_MODEL_PATH` to override
- Device: `cpu` by default, set `YOLO_DEVICE=cuda` for GPU

**Model Loading:**
- Model is loaded lazily (on first inference)
- Cached globally for subsequent requests
- Supports both `.pt` (PyTorch) and `.onnx` formats

### Dobot Service (`services/dobot_service.py`)

**Function:** `sort_with_robot(class_name: str) -> Tuple[bool, str]`

Controls the Dobot Magician robot arm to sort items.

**Workflow:**
1. Gets singleton DobotService instance
2. Auto-connects if not connected
3. Maps ML prediction class to bin position
4. Executes 9-step sorting sequence:
   - Move above pickup position
   - Descend to pickup height
   - Close gripper (pick item)
   - Lift item
   - Move above target bin
   - Descend to bin height
   - Open gripper (place item)
   - Lift up
   - Return home

**Class Mapping:**
- `paper` → paper bin
- `plastic` → plastic bin
- `cardboard` → cardboard bin
- `biological` → biological bin
- All others → trash bin

**Connection:**
- Auto-detects COM port (Windows)
- Can specify manually: `service.connect(port="COM5")`
- Singleton pattern ensures single connection

**Coordinate Configuration:**
All coordinates are defined at the top of `dobot_service.py`:
- `BIN_POSITIONS`: Bin locations for each waste class
- `PICKUP_POSITION`: Where items are placed
- `HOME_POSITION`: Safe rest position
- `PICK_HEIGHT_OFFSET`: How far down to pick
- `PLACE_HEIGHT_OFFSET`: How far down to place

See `docs/COORDINATE_ADJUSTMENT_GUIDE.md` for detailed calibration instructions.

---

## Environment Variables

### Optional Configuration

```bash
# ML Model Configuration
YOLO_MODEL_PATH=/path/to/model.pt    # Override default model path
YOLO_DEVICE=cuda                      # Use GPU (default: cpu)

# FastAPI Configuration
FASTAPI_HOST=0.0.0.0                  # Server host (default: 0.0.0.0)
FASTAPI_PORT=8000                     # Server port (default: 8000)
```

### CORS Configuration

Currently hardcoded in `main.py`:
```python
allow_origins=["http://localhost:3000"]  # Next.js dev server
```

For production, update CORS settings or use environment variables.

---

## Installation & Setup

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Dobot SDK Setup

The Dobot Magician SDK files are included in this repository at `backend/dobot_magician/`. The original SDK from Dobot has been modified to work correctly with this project.

**SDK Modifications:**

The original SDK's load() function used relative paths that failed when the script was run from different directories. The included version has been modified with the following changes:

**Original SDK issues:**
- Used "./DobotDll.dll" (relative path), which only worked when running from the SDK directory
- Used CDLL with RTLD_GLOBAL flag, which is Linux/Mac-specific and caused issues on Windows
- Could not load the DLL from any working directory

**Modifications made:**

1. Added import at the top:
   ```python
   from pathlib import Path
   ```

2. Modified the load() function to use absolute paths:
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

**What these changes accomplish:**
- Absolute path resolution: Uses Path(__file__).resolve().parent to find the DLL relative to the script's location, regardless of working directory
- Windows-specific loading: Uses WinDLL instead of CDLL on Windows (more appropriate for Windows DLLs)
- Removed RTLD_GLOBAL: This flag is Linux/Mac-specific and not needed on Windows
- macOS path fix: Also uses absolute path for macOS dylib

The SDK files in `backend/dobot_magician/` are ready to use and do not require any additional setup.

**Note:** Dobot SDK requires Windows OS.

### 4. ML Model

The trained YOLOv8 model is included in the repository at `backend/models/best.pt`. The model is ready to use. The model path can be overridden by setting the `YOLO_MODEL_PATH` environment variable if needed.

### 5. Run Backend

From project root:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or from `backend/` directory:
```bash
python main.py
```

---

## File Structure

```
backend/
├── main.py                      # FastAPI application
├── requirements.txt             # Python dependencies
│
├── services/
│   ├── camera_service.py        # ML inference & image processing
│   ├── snapshot_service.py      # DroidCam frame extraction
│   ├── dobot_service.py         # Robot control
│
├── utils/
│   └── image_utils.py           # Image conversion utilities
│
├── models/
│   ├── best.pt                  # YOLOv8 model
│   └── best.onnx                # YOLOv8 model ONNX format
│
├── frames/                      # Saved captured frames (auto-created)
│
└── dobot_magician/              # Dobot SDK files (modified version included)
    ├── DobotDll.dll
    ├── DobotDllType.py          # Modified to use absolute paths
    ├── DobotControl.py
    └── ...                      # remaining SDK files
```

---

## Dependencies

See `requirements.txt` for full list. Key dependencies:

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **pillow**: Image processing
- **ultralytics**: YOLOv8 model
- **httpx**: Async HTTP client
- **python-multipart**: File upload support

---

## Troubleshooting

### DroidCam Connection Issues

**Error:** "Failed to connect to DroidCam"
- Verify DroidCam is running on phone
- Check IP address is correct
- Ensure phone and computer are on same WiFi network
- Check firewall settings (port 4747)

**Error:** "No JPEG frame found in stream"
- DroidCam may be slow to start streaming
- Wait a few seconds and try again
- Check DroidCam app shows "connected" status

### ML Model Issues

**Error:** "Model file not found"
- Ensure model is at `backend/models/best.pt`
- Or set `YOLO_MODEL_PATH` environment variable
- Check file permissions

**Error:** "CUDA out of memory"
- Set `YOLO_DEVICE=cpu` to use CPU instead
- Or reduce batch size in model configuration

### Robot Connection Issues

**Error:** "Dobot SDK import error"
- Verify `DobotDll.dll` and `DobotDllType.py` are in `backend/dobot_magician/`
- Check Windows OS (required for Dobot SDK)
- Ensure all supporting DLLs are present

**Error:** "Failed to connect to Dobot"
- Check USB connection
- Verify COM port (check Windows Device Manager)
- Ensure no other software is using the Dobot
- Try specifying port manually: `service.connect(port="COM5")`

**Error:** "Robot doesn't move"
- Check backend console for detailed error messages
- Verify coordinates are calibrated correctly
- Test each position manually before automatic sorting
- Check gripper connection and wiring

---

## Saved Frames

Captured frames are automatically saved to `backend/frames/` with timestamp filenames:

**Format:** `frame_YYYYMMDD_HHMMSS_mmm.jpg`

**Example:** `frame_20241121_143022_456.jpg`

- **YYYYMMDD**: Date (Year-Month-Day)
- **HHMMSS**: Time (Hour-Minute-Second)
- **mmm**: Milliseconds (3 digits)

---

## Additional Resources

- **Coordinate Calibration**: See `docs/COORDINATE_ADJUSTMENT_GUIDE.md`
- **Dobot SDK**: See `dobot_magician/README.md`
- **Main Documentation**: See root `README.md`

---

*Last Updated: Based on current codebase analysis 18.12.2025*
