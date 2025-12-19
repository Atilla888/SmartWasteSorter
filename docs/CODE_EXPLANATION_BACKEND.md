# Backend Code Explanation

This document provides a detailed function-by-function and class-by-class explanation of the backend source code.

---

## Table of Contents

1. [main.py - FastAPI Application](#mainpy---fastapi-application)
2. [services/camera_service.py - ML Inference & Image Processing](#servicescamera_servicepy---ml-inference--image-processing)
3. [services/snapshot_service.py - DroidCam Frame Extraction](#servicessnapshot_servicepy---droidcam-frame-extraction)
4. [services/dobot_service.py - Robot Control](#servicesdobot_servicepy---robot-control)
5. [utils/image_utils.py - Image Utilities](#utilsimage_utilspy---image-utilities)
6. [System Interactions](#system-interactions)

---

## main.py - FastAPI Application

**Purpose:** FastAPI web server that provides REST API endpoints for the Smart Waste Sorter application. Handles HTTP requests from the frontend and routes them to appropriate service functions.

### Global Configuration

**CORS Middleware:**
- **Configuration:** Allows requests from `http://localhost:3000` (Next.js dev server)
- **Side Effects:** Enables cross-origin requests from frontend
- **System Impact:** Required for frontend-backend communication

**Path Setup:**
- Adds project root to `sys.path` to allow imports when running from different directories
- Enables both `from backend.services...` and `from services...` import styles

### Functions

#### `root() -> dict`

**Purpose:** Health check endpoint to verify API is running.

**Inputs:** None (GET request)

**Outputs:** 
- `dict`: `{"message": "Smart Waste Sorter API is running"}`

**Side Effects:** None

**System Workflow:** 
- Frontend can call this to verify backend connectivity
- No dependencies on other services

---

#### `snapshot(ip: str) -> Response`

**Purpose:** Extracts a single JPEG frame from DroidCam MJPEG stream and returns it as HTTP response.

**Inputs:**
- `ip` (Query parameter, required): DroidCam IP address (e.g., "192.168.0.105")

**Outputs:**
- `Response`: HTTP response with:
  - Content-Type: `image/jpeg`
  - Body: JPEG image bytes

**Side Effects:**
- **Network I/O:** Makes HTTP GET request to `http://{ip}:4747/video` via `extract_single_frame()`
- **Error Handling:** Raises HTTPException with appropriate status codes:
  - `400`: Invalid IP (ValueError)
  - `503`: Connection/timeout errors (ConnectionError, TimeoutError)
  - `500`: Runtime errors or unexpected exceptions

**System Workflow:**
1. Frontend calls `/api/snapshot?ip={ip}` (via Next.js API route proxy)
2. Backend calls `extract_single_frame(ip)` from `snapshot_service`
3. Returns JPEG bytes to frontend
4. Frontend uses this for frame capture before uploading

**Dependencies:**
- `services.snapshot_service.extract_single_frame()` - Performs actual frame extraction

---

#### `capture_frame(file: UploadFile) -> dict`

**Purpose:** Processes uploaded image: saves to disk, runs ML inference, triggers robot sorting.

**Inputs:**
- `file` (FormData, required): FastAPI UploadFile containing image blob

**Outputs:**
- `dict` with keys:
  - `success` (bool): True if processing succeeded
  - `saved_as` (str): Filename of saved frame (if successful)
  - `prediction` (str): ML prediction class name (if successful)
  - `confidence` (float): Confidence score 0.0-1.0 (if successful)
  - `robot_action` (str): Robot operation status message
  - `error` (str): Error message (if failed)

**Side Effects:**
- **File I/O:** Saves image to `backend/frames/` directory via `process_frame()`
- **ML Inference:** Loads YOLOv8 model (if not already loaded) and runs inference
- **Hardware:** Triggers robot sorting sequence via `sort_with_robot()`
- **Console Output:** Prints robot operation status to stdout

**System Workflow:**
1. Frontend uploads image via POST `/api/capture` (via Next.js API route proxy)
2. Backend calls `process_frame(file)` from `camera_service`
3. `process_frame()` handles:
   - Image decoding and saving
   - ML inference
   - Robot sorting trigger
4. Returns JSON response with results
5. Frontend displays prediction and robot status

**Dependencies:**
- `services.camera_service.process_frame()` - Handles entire processing pipeline

**Error Handling:**
- Catches all exceptions and returns `{"success": False, "error": str(e)}`
- Does not raise HTTPException (returns error in JSON response)

---

## services/camera_service.py - ML Inference & Image Processing

**Purpose:** Handles image processing, ML model inference, and coordinates robot sorting. Core service that ties together image capture, classification, and robotic action.

### Global Variables

**`_model: Optional[YOLO]`**
- **Purpose:** Global cached YOLOv8 model instance
- **Initialization:** `None` initially, loaded lazily on first inference
- **Lifetime:** Persists for entire application lifetime after first load
- **System Impact:** Prevents redundant model loading, improves performance

**`MODEL_PATH: Path`**
- **Purpose:** Path to YOLOv8 model file
- **Resolution:** 
  - Checks `YOLO_MODEL_PATH` environment variable first
  - Defaults to `backend/models/best.pt` if not set
- **System Impact:** Allows model path override via environment variable

**`MODEL_DEVICE: str`**
- **Purpose:** Device for ML inference (CPU or GPU)
- **Default:** `"cpu"` (from `YOLO_DEVICE` env var, or "cpu")
- **System Impact:** Controls whether inference runs on CPU or CUDA GPU

**`FRAMES_DIR: Path`**
- **Purpose:** Directory path for saving captured frames
- **Value:** `backend/frames/`
- **System Impact:** All captured frames saved here with timestamp filenames

### Functions

#### `_load_model() -> YOLO`

**Purpose:** Lazy-loads YOLOv8 classification model. Loads model once and caches globally.

**Inputs:** None

**Outputs:**
- `YOLO`: Ultralytics YOLO model instance

**Side Effects:**
- **File I/O:** Reads model file from disk (`MODEL_PATH`)
- **Memory:** Loads model into memory (can be large, ~50-200MB depending on model size)
- **Global State:** Sets `_model` global variable
- **Exception:** Raises `FileNotFoundError` if model file doesn't exist

**System Workflow:**
- Called automatically by `run_inference()` on first inference
- Subsequent calls return cached model (no reload)
- Model remains in memory for all subsequent requests

**Dependencies:**
- `ultralytics.YOLO` - External library for model loading
- `MODEL_PATH` - Must point to valid `.pt` or `.onnx` model file

---

#### `ensure_frames_directory() -> None`

**Purpose:** Creates `backend/frames/` directory if it doesn't exist.

**Inputs:** None

**Outputs:** None

**Side Effects:**
- **File I/O:** Creates directory structure if missing
- **No Exception:** Uses `exist_ok=True`, won't raise if directory exists

**System Workflow:**
- Called by `process_frame()` before saving images
- Ensures directory exists before file operations

---

#### `run_inference(image: Image.Image) -> dict`

**Purpose:** Runs YOLOv8 classification inference on a PIL Image and returns top-1 prediction.

**Inputs:**
- `image` (PIL.Image.Image): Image in RGB format (any size)

**Outputs:**
- `dict` with keys:
  - `prediction` (str): Class name (e.g., "plastic", "paper")
  - `confidence` (float): Confidence score 0.0-1.0

**Side Effects:**
- **Model Loading:** Calls `_load_model()` (lazy loading on first call)
- **Image Processing:** 
  - Converts image to RGB if not already
  - YOLO automatically resizes to 224×224 internally
- **ML Computation:** Runs neural network inference (CPU/GPU intensive)
- **Exception:** Raises `FileNotFoundError` if model missing, `RuntimeError` if inference fails

**System Workflow:**
1. Called by `process_frame()` after image is decoded
2. Model loaded (if not already cached)
3. Image preprocessed (RGB conversion, auto-resize by YOLO)
4. Inference runs, returns top-1 class and confidence
5. Result used to trigger robot sorting

**Dependencies:**
- `_load_model()` - Loads/caches model
- `ultralytics.YOLO` - Performs inference
- `MODEL_DEVICE` - Controls CPU/GPU execution

**Model Output Format:**
- YOLO returns `Results` object with `probs` attribute
- `probs.top1` = class index
- `probs.top1conf` = confidence score
- `result.names[top1_idx]` = class name string

---

#### `process_frame(file: UploadFile) -> dict`

**Purpose:** Main processing function. Decodes uploaded image, saves to disk, runs ML inference, and triggers robot sorting.

**Inputs:**
- `file` (FastAPI.UploadFile): Uploaded image file from HTTP request

**Outputs:**
- `dict` with keys:
  - `success` (bool): True if processing succeeded
  - `saved_as` (str): Timestamp-based filename (e.g., "frame_20241121_143022_456.jpg")
  - `prediction` (str): ML prediction class name
  - `confidence` (float): Confidence score
  - `robot_action` (str): Robot operation status message
  - `error` (str): Error message (if `success=False`)

**Side Effects:**
- **File I/O:** 
  - Reads uploaded file bytes
  - Saves image to `backend/frames/` with timestamp filename
- **ML Inference:** Calls `run_inference()` (may load model on first call)
- **Hardware:** Calls `sort_with_robot()` which triggers robot movement
- **Console Output:** Prints robot operation status with separators
- **Exception Handling:** Catches all exceptions, returns error dict instead of raising

**System Workflow:**
1. Called by FastAPI `/capture` endpoint
2. Ensures frames directory exists
3. Decodes UploadFile to PIL Image via `read_upload_image()`
4. Generates timestamp filename (format: `frame_YYYYMMDD_HHMMSS_mmm.jpg`)
5. Saves image to disk
6. Runs ML inference via `run_inference()`
7. Triggers robot sorting via `sort_with_robot(prediction)`
8. Builds response dict with all results
9. Returns to FastAPI endpoint

**Dependencies:**
- `ensure_frames_directory()` - Creates directory
- `utils.image_utils.read_upload_image()` - Decodes file
- `run_inference()` - ML classification
- `services.dobot_service.sort_with_robot()` - Robot control

**Error Handling:**
- Wraps entire function in try-except
- Returns `{"success": False, "error": str(e)}` on any exception
- Robot errors are caught and included in response, but don't fail the entire operation

**Timestamp Format:**
- `datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]`
- `%Y%m%d`: Date (20241121)
- `%H%M%S`: Time (143022)
- `%f`: Microseconds, truncated to 3 digits (milliseconds: 456)

---

## services/snapshot_service.py - DroidCam Frame Extraction

**Purpose:** Extracts a single JPEG frame from DroidCam MJPEG video stream by parsing JPEG markers.

### Constants

**`JPEG_START = b'\xff\xd8'`**
- **Purpose:** JPEG Start of Image (SOI) marker
- **Usage:** Identifies beginning of JPEG frame in stream

**`JPEG_END = b'\xff\xd9'`**
- **Purpose:** JPEG End of Image (EOI) marker
- **Usage:** Identifies end of JPEG frame in stream

**`MAX_FRAME_BYTES = 1_500_000`**
- **Purpose:** Safety limit to prevent runaway buffering (1.5 MB)
- **Usage:** Raises error if frame exceeds this size

**`CHUNK_SIZE = 4096`**
- **Purpose:** Bytes to read per iteration from HTTP stream
- **Usage:** Controls streaming buffer size

### Functions

#### `extract_single_frame(ip: str, timeout: float = 10.0) -> bytes`

**Purpose:** Connects to DroidCam MJPEG stream and extracts the first complete JPEG frame by finding SOI/EOI markers.

**Inputs:**
- `ip` (str): DroidCam IP address (e.g., "192.168.0.105")
- `timeout` (float, optional): HTTP request timeout in seconds (default: 10.0)

**Outputs:**
- `bytes`: Complete JPEG image bytes (from SOI to EOI markers inclusive)

**Side Effects:**
- **Network I/O:** 
  - Makes async HTTP GET request to `http://{ip}:4747/video`
  - Streams response data byte-by-byte
  - Closes connection after frame extraction
- **Memory:** Buffers stream data until complete frame found (max 1.5 MB)
- **Exception:** Raises:
  - `ValueError`: If IP is empty or invalid
  - `ConnectionError`: If connection fails or status code != 200
  - `TimeoutError`: If request times out
  - `RuntimeError`: If no JPEG frame found, incomplete frame, or frame too large

**System Workflow:**
1. Called by FastAPI `/snapshot` endpoint
2. Validates IP address
3. Connects to DroidCam MJPEG stream via httpx
4. Reads stream in 4KB chunks
5. Searches for JPEG start marker (`0xFF 0xD8`)
6. Once found, searches for JPEG end marker (`0xFF 0xD9`)
7. Extracts complete frame between markers
8. Returns JPEG bytes
9. Frontend receives JPEG blob for upload

**Dependencies:**
- `httpx` - Async HTTP client for streaming

**Algorithm:**
1. Initialize empty buffer
2. Read stream chunks into buffer
3. Check buffer size (raise error if > MAX_FRAME_BYTES)
4. Search for SOI marker in buffer
5. Once SOI found, trim buffer to start from SOI
6. Continue reading, search for EOI marker
7. Once EOI found, extract bytes from SOI to EOI (inclusive)
8. Return complete JPEG frame

**Error Cases:**
- **No SOI found:** Stream doesn't contain JPEG data
- **SOI found but no EOI:** Incomplete frame (stream ended prematurely)
- **Buffer exceeds limit:** Stream corrupted or not JPEG format
- **Connection fails:** DroidCam not running, wrong IP, network issue
- **Timeout:** DroidCam slow to respond or network latency

**Why Single Frame:**
- DroidCam Free only allows one connection to `/video` stream
- Preview and capture cannot run simultaneously
- Solution: Extract one frame, close connection, allow preview to resume

---

## services/dobot_service.py - Robot Control

**Purpose:** Provides singleton service for controlling Dobot Magician robotic arm. Handles connection management, movement commands, and complete sorting sequences.

### Global Constants

**`DOBOT_AVAILABLE: bool`**
- **Purpose:** Flag indicating if Dobot SDK is importable
- **Set:** True if `DobotDllType` imports successfully, False otherwise
- **System Impact:** Prevents errors if SDK files missing

**`BIN_POSITIONS: dict`**
- **Purpose:** Maps waste class names to robot bin coordinates
- **Format:** `{class_name: (x, y, z, r)}` in millimeters
- **Keys:** "paper", "plastic", "glass", "biological", "trash"
- **Values:** Tuple of (x, y, z, rotation) coordinates
- **System Impact:** Defines where robot places items for each waste type

**`PICKUP_POSITION: tuple`**
- **Purpose:** Coordinates where items are placed for robot to pick up
- **Format:** `(x, y, z, r)` in millimeters
- **System Impact:** Robot moves here first in sorting sequence

**`HOME_POSITION: tuple`**
- **Purpose:** Safe rest position where robot returns after sorting
- **Format:** `(x, y, z, r)` in millimeters
- **System Impact:** Robot moves here at end of sequence

**`PICK_HEIGHT_OFFSET: int`**
- **Purpose:** How far below pickup Z position robot descends when picking
- **Value:** Negative number (e.g., -20 mm)
- **System Impact:** Controls gripper descent depth for picking

**`PLACE_HEIGHT_OFFSET: int`**
- **Purpose:** How far below bin Z position robot descends when placing
- **Value:** Negative number (e.g., -10 mm)
- **System Impact:** Controls gripper descent depth for placing

**`MOVE_SPEED: int`**
- **Purpose:** Robot movement speed (currently not used in code, defined but unused)
- **Value:** 200 mm/s

**`MOVE_ACCELERATION: int`**
- **Purpose:** Robot movement acceleration (currently not used in code, defined but unused)
- **Value:** 40 mm/s²

### Functions

#### `map_class_to_bin(ml_prediction: str) -> str`

**Purpose:** Maps ML model prediction class names to robot bin class names. Handles 12 ML classes → 5 physical bins.

**Inputs:**
- `ml_prediction` (str): ML model prediction class name (e.g., "plastic", "brown-glass", "metal")

**Outputs:**
- `str`: Robot bin class name: "paper", "plastic", "glass", "biological", or "trash"

**Side Effects:** None (pure function)

**System Workflow:**
- Called by `sort_item()` to map ML prediction to bin
- Handles class name normalization (lowercase, strip)
- Maps glass variants (brown-glass, green-glass, white-glass) → "glass"
- Maps all unrecognized classes → "trash"

**Mapping Rules:**
- Direct matches: "paper" → "paper", "plastic" → "plastic", "biological" → "biological"
- Glass variants: "brown-glass", "green-glass", "white-glass", "glass" → "glass"
- All others: → "trash"

---

### Class: `DobotService`

**Purpose:** Singleton service class for Dobot robot control. Manages connection, movement commands, and sorting sequences.

#### Class Variables

**`_instance: Optional[DobotService]`**
- **Purpose:** Singleton instance storage
- **Access:** Private class variable

**`_api: Optional[object]`**
- **Purpose:** Dobot SDK API object (from `DobotDllType.load()`)
- **Lifetime:** Set on connection, cleared on disconnect

**`_connected: bool`**
- **Purpose:** Connection status flag
- **Set:** True after successful `connect()`, False on disconnect

**`_port: Optional[str]`**
- **Purpose:** COM port name (e.g., "COM5")
- **Set:** On successful connection

**`_sorting_in_progress: bool`**
- **Purpose:** Flag to prevent concurrent sorting operations
- **Set:** True at start of `sort_item()`, False in finally block

#### Methods

##### `__new__(cls) -> DobotService`

**Purpose:** Singleton pattern implementation. Ensures only one instance exists.

**Inputs:** `cls` (class)

**Outputs:** `DobotService` instance (same instance on all calls)

**Side Effects:** Creates instance only on first call, returns existing on subsequent calls

**System Impact:** Guarantees single robot connection across entire application

---

##### `__init__(self) -> None`

**Purpose:** Initializes service instance. Sets `_sorting_in_progress` flag.

**Inputs:** `self`

**Outputs:** None

**Side Effects:** 
- Sets `_sorting_in_progress = False`
- Sets `_connected = False` if SDK unavailable

---

##### `_find_dobot_port(self) -> Optional[str]`

**Purpose:** Automatically detects Dobot COM port by trying common ports.

**Inputs:** `self`

**Outputs:**
- `Optional[str]`: Port name (e.g., "COM5") or None if not found

**Side Effects:**
- **Hardware:** Attempts connection to each port (temporary connections)
- **Network I/O:** Calls `dType.ConnectDobot()` for each port
- **Exception:** Silently catches exceptions during port detection

**System Workflow:**
- Called by `connect()` if port not specified
- Tries ports in order: COM5, COM4, COM3, COM6, COM7, COM8
- Returns first port that successfully connects
- Disconnects test connection before returning

**Dependencies:**
- `DobotDllType.load()` - Loads SDK
- `DobotDllType.ConnectDobot()` - Tests connection
- `DobotDllType.DisconnectDobot()` - Closes test connection

---

##### `connect(port: Optional[str] = None, baudrate: int = 115200) -> bool`

**Purpose:** Connects to Dobot robot via USB/Serial. Auto-detects port if not provided.

**Inputs:**
- `port` (Optional[str]): COM port name (e.g., "COM5"). If None or "", auto-detects.
- `baudrate` (int): Serial baudrate (default: 115200)

**Outputs:**
- `bool`: True if connected successfully, False otherwise

**Side Effects:**
- **Hardware:** 
  - Loads Dobot DLL via `dType.load()`
  - Establishes USB/Serial connection to robot
  - Configures motion parameters
  - Executes HOME command to activate motors
- **Global State:** 
  - Sets `_api`, `_connected`, `_port`
  - Clears command queue
- **Console Output:** Prints connection status
- **Exception:** Returns False on any error, prints error message

**System Workflow:**
1. Checks if already connected (returns True if yes)
2. Loads Dobot SDK DLL
3. Auto-detects port if not provided (via `_find_dobot_port()`)
4. Calls `dType.ConnectDobot()` to establish connection
5. Clears command queue
6. Sets motion parameters (joint params, common params)
7. Starts command queue execution
8. Runs HOME command to activate motors
9. Waits for HOME to complete
10. Sets connection flags

**Dependencies:**
- `DobotDllType.load()` - Loads SDK
- `DobotDllType.ConnectDobot()` - Connects to robot
- `DobotDllType.SetQueuedCmdClear()` - Clears queue
- `DobotDllType.SetPTPJointParams()` - Sets joint parameters
- `DobotDllType.SetPTPCommonParams()` - Sets common parameters
- `DobotDllType.SetQueuedCmdStartExec()` - Starts execution
- `DobotDllType.SetHOMECmd()` - Home command
- `DobotDllType.GetQueuedCmdCurrentIndex()` - Checks queue status

**Error Handling:**
- Returns False on any exception
- Prints error message to console
- Resets `_api` and `_connected` on failure

---

##### `disconnect(self) -> None`

**Purpose:** Disconnects from Dobot robot and cleans up resources.

**Inputs:** `self`

**Outputs:** None

**Side Effects:**
- **Hardware:** 
  - Stops command queue execution
  - Closes USB/Serial connection
- **Global State:** 
  - Sets `_api = None`
  - Sets `_connected = False`
  - Sets `_port = None`
- **Exception:** Catches and prints errors during disconnect

**System Workflow:**
- Called on application shutdown or manual disconnect
- Stops all robot movement
- Releases COM port for other applications

**Dependencies:**
- `DobotDllType.SetQueuedCmdStopExec()` - Stops execution
- `DobotDllType.DisconnectDobot()` - Closes connection

---

##### `is_connected(self) -> bool`

**Purpose:** Checks if robot is currently connected.

**Inputs:** `self`

**Outputs:**
- `bool`: True if connected, False otherwise

**Side Effects:** None

**System Workflow:**
- Used by other methods to verify connection before operations
- Used by `sort_with_robot()` to auto-connect if needed

---

##### `_ensure_connected(self) -> None`

**Purpose:** Raises error if robot is not connected. Used internally by movement methods.

**Inputs:** `self`

**Outputs:** None

**Side Effects:**
- **Exception:** Raises `RuntimeError` if not connected

**System Workflow:**
- Called by movement methods before executing commands
- Ensures connection exists before hardware operations

---

##### `move_to(x: float, y: float, z: float, r: float = 0, wait: bool = True) -> bool`

**Purpose:** Moves robot to specified position using PTP (Point-to-Point) movement.

**Inputs:**
- `x` (float): X coordinate in millimeters
- `y` (float): Y coordinate in millimeters
- `z` (float): Z coordinate in millimeters
- `r` (float): Rotation angle in degrees (default: 0)
- `wait` (bool): If True, waits for movement to complete (default: True)

**Outputs:**
- `bool`: True if successful, False otherwise

**Side Effects:**
- **Hardware:** 
  - Sends PTP movement command to robot
  - Robot physically moves to specified position
  - Blocks until movement completes (if `wait=True`)
- **Console Output:** Prints movement status
- **Time:** Waits up to 15 seconds for movement completion
- **Exception:** Returns False on error, prints error message

**System Workflow:**
1. Checks connection status
2. Prints target coordinates
3. Calls `dType.SetPTPCmd()` with PTPMOVJXYZMode (joint movement)
4. Queues command (isQueued=1)
5. If `wait=True`:
   - Polls `GetQueuedCmdCurrentIndex()` until command executed
   - Times out after 15 seconds
   - Waits additional 300ms for stability
6. Returns success/failure

**Dependencies:**
- `DobotDllType.SetPTPCmd()` - Sends movement command
- `DobotDllType.GetQueuedCmdCurrentIndex()` - Checks execution status
- `DobotDllType.dSleep()` - Sleeps between polls

**Blocking Behavior:**
- All movements are blocking (wait for completion)
- This causes API endpoint to block during robot operations (~10-15 seconds per sequence)
- No async/background execution

---

##### `pick(self) -> bool`

**Purpose:** Closes gripper to pick up object.

**Inputs:** `self`

**Outputs:**
- `bool`: True if successful, False otherwise

**Side Effects:**
- **Hardware:** 
  - Sends gripper close command to robot
  - Gripper physically closes (mechanical gripper fingers come together)
  - Waits for command to execute (up to 2 seconds)
  - Waits additional 500ms for gripper to fully close
- **Console Output:** Prints gripper status
- **Exception:** Returns False on error

**System Workflow:**
1. Checks connection
2. Calls `dType.SetEndEffectorGripper(api, 1, 1)`:
   - `enableCtrl=1`: Enable gripper control
   - `on=1`: Close gripper (grip object)
3. Waits for command to execute (polls queue index)
4. Waits additional 500ms for physical closure
5. Returns success/failure

**Dependencies:**
- `DobotDllType.SetEndEffectorGripper()` - Controls gripper
- `DobotDllType.GetQueuedCmdCurrentIndex()` - Checks execution

**Gripper Mechanism:**
- Dobot Magician uses mechanical gripper (two-finger)
- `on=1` closes gripper (fingers come together)
- `on=0` opens gripper (fingers spread apart)

---

##### `place(self) -> bool`

**Purpose:** Opens gripper to place/release object.

**Inputs:** `self`

**Outputs:**
- `bool`: True if successful, False otherwise

**Side Effects:**
- **Hardware:** 
  - Sends gripper open command to robot
  - Gripper physically opens (mechanical gripper fingers spread apart)
  - Waits for command to execute (up to 2 seconds)
  - Waits additional 500ms for gripper to fully open
- **Console Output:** Prints gripper status
- **Exception:** Returns False on error

**System Workflow:**
1. Checks connection
2. Calls `dType.SetEndEffectorGripper(api, 1, 0)`:
   - `enableCtrl=1`: Keep control enabled
   - `on=0`: Open gripper (release object)
3. Waits for command to execute (polls queue index)
4. Waits additional 500ms for physical opening
5. Returns success/failure

**Dependencies:**
- `DobotDllType.SetEndEffectorGripper()` - Controls gripper
- `DobotDllType.GetQueuedCmdCurrentIndex()` - Checks execution

---

##### `home(self) -> bool`

**Purpose:** Moves robot to home position using SDK HOME command.

**Inputs:** `self`

**Outputs:**
- `bool`: True if successful, False otherwise

**Side Effects:**
- **Hardware:** 
  - Sends HOME command to robot
  - Robot moves to predefined home position
  - Waits for movement to complete (up to 15 seconds)
  - Waits additional 1000ms for stability
- **Console Output:** None (silent)
- **Exception:** Falls back to manual `move_to(HOME_POSITION)` if HOME command fails

**System Workflow:**
1. Checks connection
2. Calls `dType.SetHOMECmd(api, temp=0, isQueued=1)`
3. Waits for command to execute (polls queue index, 15s timeout)
4. Waits additional 1000ms
5. If HOME command fails, falls back to `move_to(HOME_POSITION)`
6. Returns success/failure

**Dependencies:**
- `DobotDllType.SetHOMECmd()` - Home command
- `DobotDllType.GetQueuedCmdCurrentIndex()` - Checks execution
- `move_to()` - Fallback manual home

---

##### `sort_item(class_name: str) -> Tuple[bool, str]`

**Purpose:** Executes complete 9-step sorting sequence: pick item, move to bin, place, return home.

**Inputs:**
- `class_name` (str): ML prediction class name (e.g., "plastic", "brown-glass", "metal")

**Outputs:**
- `Tuple[bool, str]`: (success, message)
  - `success`: True if sequence completed, False on error
  - `message`: Status message (e.g., "Sorted to PLASTIC bin")

**Side Effects:**
- **Hardware:** 
  - Executes 9 sequential robot movements:
    1. Move above pickup position
    2. Descend to pickup height
    3. Close gripper (pick)
    4. Lift item
    5. Move above bin
    6. Descend to bin height
    7. Open gripper (place)
    8. Lift up
    9. Return home
  - Each step blocks until completion (~10-15 seconds total)
- **Console Output:** 
  - Prints detailed step-by-step progress
  - Prints coordinate configuration for debugging
  - Prints gripper state at each step
- **Global State:** 
  - Sets `_sorting_in_progress = True` at start
  - Resets to False in finally block (prevents concurrent operations)
- **Exception:** Returns (False, error_message) on any error, prints traceback

**System Workflow:**
1. Checks if sorting already in progress (prevents concurrent operations)
2. Checks connection status
3. Sets `_sorting_in_progress = True`
4. Maps ML class to bin class via `map_class_to_bin()`
5. Gets bin coordinates from `BIN_POSITIONS`
6. Validates coordinates (warns if unusual)
7. Executes 9-step sequence:
   - **Steps 1-4:** Pickup phase (gripper opens → closes)
   - **Steps 5-6:** Movement phase (gripper closed, holding object)
   - **Steps 7-8:** Place phase (gripper opens)
   - **Step 9:** Return phase (gripper open, return home)
8. Builds success message
9. Returns (True, message) or (False, error_message)
10. Always resets `_sorting_in_progress` in finally block

**Dependencies:**
- `map_class_to_bin()` - Maps ML class to bin
- `move_to()` - Movement commands
- `pick()` - Gripper close
- `place()` - Gripper open
- `home()` - Return home

**Coordinate Calculations:**
- **Above pickup:** `(pickup_x, pickup_y, pickup_z + 20, pickup_r)`
- **Pickup level:** `(pickup_x, pickup_y, pickup_z + PICK_HEIGHT_OFFSET, pickup_r)`
- **Above bin:** `(bin_x, bin_y, bin_z + 20, bin_r)`
- **Bin level:** `(bin_x, bin_y, bin_z + PLACE_HEIGHT_OFFSET, bin_r)`

**Error Handling:**
- Returns (False, error_message) on any step failure
- Prints full traceback for debugging
- Always resets `_sorting_in_progress` flag (prevents deadlock)

**Gripper State Sequence:**
- Steps 1-2: OPEN (approaching item)
- Step 3: CLOSES (picks item)
- Steps 4-6: CLOSED (holding item)
- Step 7: OPENS (releases item)
- Steps 8-9: OPEN (returning home)

---

### Module-Level Functions

#### `get_dobot_service() -> DobotService`

**Purpose:** Returns global singleton DobotService instance.

**Inputs:** None

**Outputs:**
- `DobotService`: Singleton service instance

**Side Effects:**
- **Global State:** Creates instance on first call, returns existing on subsequent calls

**System Workflow:**
- Called by `sort_with_robot()` to get service instance
- Ensures only one instance exists (singleton pattern)

---

#### `sort_with_robot(class_name: str) -> Tuple[bool, str]`

**Purpose:** Convenience function to sort item using robot. Auto-connects if needed.

**Inputs:**
- `class_name` (str): ML prediction class name

**Outputs:**
- `Tuple[bool, str]`: (success, message)

**Side Effects:**
- **Hardware:** 
  - Auto-connects robot if not connected
  - Triggers full sorting sequence
- **Console Output:** 
  - Prints detailed operation status
  - Prints troubleshooting info on connection failure
- **Exception:** Returns (False, error_message) on any error

**System Workflow:**
1. Checks if Dobot SDK available (returns error if not)
2. Gets singleton service instance
3. Auto-connects if not connected (calls `connect()`)
4. Calls `service.sort_item(class_name)`
5. Returns result

**Dependencies:**
- `get_dobot_service()` - Gets service instance
- `DobotService.connect()` - Auto-connection
- `DobotService.sort_item()` - Sorting sequence

**Called By:**
- `camera_service.process_frame()` - After ML inference

**System Integration:**
- This is the entry point from camera service to robot control
- Handles all connection management automatically
- Provides user-friendly error messages

---

## utils/image_utils.py - Image Utilities

**Purpose:** Utility functions for image format conversion and processing.

### Functions

#### `read_upload_image(file: UploadFile) -> Image.Image`

**Purpose:** Converts FastAPI UploadFile to PIL Image in RGB format.

**Inputs:**
- `file` (FastAPI.UploadFile): Uploaded file from HTTP request

**Outputs:**
- `PIL.Image.Image`: Image in RGB format

**Side Effects:**
- **File I/O:** Reads file bytes from `file.file`
- **Memory:** Loads entire image into memory
- **Image Processing:** Converts image to RGB (handles RGBA, grayscale, etc.)

**System Workflow:**
1. Called by `camera_service.process_frame()`
2. Reads bytes from UploadFile
3. Creates PIL Image from bytes (via BytesIO)
4. Converts to RGB format (ensures consistent format for ML model)
5. Returns PIL Image

**Dependencies:**
- `PIL.Image` - Image processing
- `io.BytesIO` - Byte stream handling

**Format Handling:**
- Handles any image format (JPEG, PNG, etc.)
- Converts RGBA → RGB (drops alpha channel)
- Converts grayscale → RGB (3-channel)
- Ensures all images are RGB before ML inference

---

## System Interactions

### Frontend → Backend Flow

**1. Frame Capture Request:**
- Frontend: `GET /api/snapshot?ip={ip}` (via Next.js proxy)
- Backend: `main.py:snapshot()` → `snapshot_service.extract_single_frame()`
- Network: HTTP GET to DroidCam MJPEG stream
- Output: JPEG bytes returned to frontend

**2. Image Processing Request:**
- Frontend: `POST /api/capture` with FormData (via Next.js proxy)
- Backend: `main.py:capture_frame()` → `camera_service.process_frame()`
- Processing:
  - `image_utils.read_upload_image()` - Decode file
  - `camera_service.run_inference()` - ML classification
  - `dobot_service.sort_with_robot()` - Robot sorting
- Output: JSON response with prediction, confidence, robot status

### ML Model Integration

**Model Loading:**
- Lazy loading: Model loaded on first inference call
- Caching: Model stored in global `_model` variable
- Path: `backend/models/best.pt` (or `YOLO_MODEL_PATH` env var)
- Device: CPU (default) or CUDA GPU (via `YOLO_DEVICE` env var)

**Inference Pipeline:**
1. `process_frame()` receives UploadFile
2. `read_upload_image()` converts to PIL Image (RGB)
3. Image saved to disk (for debugging/analysis)
4. `run_inference()` called with PIL Image
5. `_load_model()` loads/caches YOLO model
6. YOLO automatically resizes image to 224×224
7. Model inference runs (CPU/GPU)
8. Top-1 prediction and confidence extracted
9. Result returned to `process_frame()`

**Model Output:**
- YOLO returns `Results` object
- `result.probs.top1` = class index
- `result.probs.top1conf` = confidence (0.0-1.0)
- `result.names[top1_idx]` = class name string

### Hardware Integration

**Dobot Robot Connection:**
- **Initialization:** `DobotService` singleton created on first use
- **Connection:** Auto-connects on first `sort_with_robot()` call
- **Port Detection:** Auto-detects COM port (tries COM5, COM4, COM3, etc.)
- **SDK Loading:** Loads `DobotDll.dll` via `DobotDllType.load()`
- **Hardware Setup:** 
  - Clears command queue
  - Sets motion parameters
  - Runs HOME command to activate motors

**Robot Control Flow:**
1. `process_frame()` calls `sort_with_robot(prediction)`
2. `sort_with_robot()` gets singleton service
3. Auto-connects if not connected
4. Maps ML class to bin class
5. Calls `service.sort_item(bin_class)`
6. Executes 9-step sequence (blocking, ~10-15 seconds)
7. Returns success/failure status

**Blocking Behavior:**
- All robot movements are blocking (wait for completion)
- API endpoint blocks during robot sequence
- No async/background execution
- Frontend waits for full sequence before receiving response

### Camera Integration

**DroidCam Frame Extraction:**
- **Connection:** HTTP GET to `http://{ip}:4747/video` (MJPEG stream)
- **Protocol:** MJPEG (Motion JPEG) - sequential JPEG frames
- **Extraction:** Parses JPEG markers (SOI `0xFF 0xD8`, EOI `0xFF 0xD9`)
- **Limitation:** DroidCam Free allows only one connection at a time
- **Solution:** Preview pauses, frame extracted, preview resumes

**Frame Extraction Flow:**
1. Frontend pauses MJPEG preview (releases connection)
2. Frontend calls `/api/snapshot?ip={ip}`
3. Backend connects to DroidCam stream
4. Backend reads stream byte-by-byte
5. Backend finds JPEG SOI/EOI markers
6. Backend extracts complete JPEG frame
7. Backend returns JPEG bytes
8. Frontend receives blob, uploads to `/api/capture`

### Error Handling Patterns

**Service-Level Errors:**
- Services catch exceptions and return error dicts/tuples
- Do not raise exceptions to FastAPI (return error in response)

**FastAPI-Level Errors:**
- `/snapshot`: Raises HTTPException with status codes (400, 503, 500)
- `/capture`: Returns error dict in JSON response (does not raise)

**Robot Errors:**
- Robot errors caught in `process_frame()`
- Error message included in response, but prediction still returned
- Robot failure does not fail entire operation

**Connection Errors:**
- DroidCam: Raises ConnectionError/TimeoutError → HTTP 503
- Dobot: Returns (False, error_message) → Included in response

### Data Flow Summary

```
Frontend Request
  ↓
FastAPI Endpoint (main.py)
  ↓
Service Function (services/*.py)
  ↓
Utility Function (utils/*.py) [if needed]
  ↓
External Library/Hardware
  - YOLO (ML inference)
  - Dobot SDK (robot control)
  - httpx (DroidCam connection)
  ↓
Response to Frontend
```

### State Management

**Global State:**
- `_model` (camera_service): Cached YOLO model instance
- `_dobot_service` (dobot_service): Singleton robot service
- `_api`, `_connected`, `_port` (DobotService): Robot connection state
- `_sorting_in_progress` (DobotService): Prevents concurrent sorting

**File System State:**
- `backend/frames/`: Directory for saved images (auto-created)
- Images saved with timestamp filenames

**Hardware State:**
- Dobot robot: Physical position, gripper state
- Connection: USB/Serial connection to robot
- Command queue: Queued robot commands

---

## Summary

The backend is organized into clear layers:

1. **API Layer** (`main.py`): HTTP endpoints, request/response handling
2. **Service Layer** (`services/*.py`): Business logic, ML inference, robot control
3. **Utility Layer** (`utils/*.py`): Helper functions for common operations

Key design patterns:
- **Singleton:** DobotService ensures single robot connection
- **Lazy Loading:** ML model loaded on first use, cached globally
- **Blocking Operations:** Robot movements block until completion
- **Error Handling:** Services return error dicts/tuples, don't raise exceptions
- **Auto-Connection:** Robot auto-connects on first use

The system integrates:
- **Computer Vision:** DroidCam frame extraction
- **Machine Learning:** YOLOv8 classification
- **Robotics:** Dobot Magician control
- **Web API:** FastAPI REST endpoints

All components work together to provide end-to-end automated waste sorting from image capture to physical robot action.
