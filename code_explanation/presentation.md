# Smart Waste Sorter - Project Presentation

## 1. Introduction

### Project Topic
Automated waste sorting system combining computer vision, machine learning, and robotics to classify and physically sort waste items using a robotic arm.

### Project Goal
Develop a full-stack application that:
- Captures images from a mobile camera stream
- Classifies waste items using deep learning
- Automatically controls a Dobot Magician robot arm to sort items into appropriate bins

### Problem Being Solved
Manual waste sorting is time-consuming and error-prone. This project demonstrates an end-to-end automated solution that integrates:
- Real-time camera input (DroidCam from phone)
- Machine learning classification (YOLOv8)
- Robotic manipulation (Dobot Magician arm)

The system provides a complete pipeline from image capture to physical sorting, showcasing practical integration of computer vision and robotics technologies.

---

## 2. Essential Theory (Short & Focused)

### YOLOv8 Classification
- **What it is**: A deep learning model that classifies images into predefined categories
- **How it works**: 
  - Takes an RGB image as input (automatically resized to 224×224)
  - Passes through a convolutional neural network backbone
  - Outputs probability scores for each class (12 waste categories in our case)
  - Returns the top-1 prediction with confidence score
- **Why YOLOv8**: Pre-trained architecture, easy to fine-tune, supports both PyTorch and ONNX formats, handles image preprocessing automatically

### MJPEG Streaming
- **What it is**: Motion JPEG - a video format where each frame is a complete JPEG image
- **How it works**: 
  - Stream consists of sequential JPEG frames delimited by markers:
    - `0xFF 0xD8` (Start of Image - SOI)
    - `0xFF 0xD9` (End of Image - EOI)
  - Each frame is self-contained (no inter-frame dependencies)
  - Can extract individual frames by finding SOI/EOI markers
- **Why MJPEG**: Simple to parse, works over HTTP, each frame is independently decodable

### Robot Control (Dobot SDK)
- **What it is**: Low-level API for controlling robotic arm movements
- **How it works**:
  - Commands sent via USB/Serial connection (COM port on Windows)
  - Position-based control: specify (x, y, z, rotation) coordinates
  - Blocking operations: each movement command waits for completion
  - Gripper control: open/close commands for picking and placing
- **Why this approach**: Direct hardware control, precise positioning, deterministic execution

---

## 3. Practical Implementation (MAIN CONTENT)

### System Architecture

**Hardware Components:**
- **DroidCam** (phone app): Provides MJPEG video stream over WiFi (port 4747)
- **Dobot Magician**: 4-axis robotic arm with gripper end effector, connected via USB
- **Computer**: Runs both frontend (Next.js) and backend (FastAPI) services

**Software Stack:**
- **Frontend**: Next.js 16 (React, TypeScript) - user interface and camera preview
- **Backend**: FastAPI (Python) - image processing, ML inference, robot control
- **ML Model**: YOLOv8 classification model (trained on 12 waste categories)
- **Robot SDK**: Dobot Windows DLL with Python wrapper

### Complete Pipeline: Input → Processing → Output

#### Phase 1: Image Capture

**User Action:**
1. User enters DroidCam IP address and clicks "Connect Camera"
2. Frontend displays live MJPEG preview stream (`http://{ip}:4747/video`)
3. User clicks "Capture & Send" button

**Frame Extraction Process:**
1. **Preview Pause**: Frontend sets `previewPaused=true`, which sets image `src=""` to release the MJPEG connection
2. **Wait Period**: 250ms delay to allow DroidCam to free the stream connection
3. **Backend Snapshot Request**: Frontend calls `/api/snapshot?ip={ip}`
4. **Backend Frame Extraction**:
   - Connects to `http://{ip}:4747/video` (MJPEG stream)
   - Reads stream byte-by-byte until finding JPEG markers
   - Extracts complete frame between SOI (`0xFF 0xD8`) and EOI (`0xFF 0xD9`) markers
   - Returns JPEG bytes to frontend
5. **Preview Resume**: Frontend automatically resumes preview after capture

**Why Single Frame Extraction:**
- DroidCam Free version only allows **one active connection** to the `/video` stream
- Preview and capture cannot run simultaneously
- Solution: Temporarily pause preview, extract frame, resume preview
- This is a **DroidCam limitation**, not a design choice

#### Phase 2: Image Processing & ML Inference

**Upload & Processing:**
1. Frontend creates `FormData` with captured JPEG blob
2. POST request to `/api/capture` endpoint
3. Backend receives `UploadFile` and decodes to PIL Image (RGB format)
4. Image saved to `backend/frames/` with timestamp filename

**ML Inference:**
1. **Model Loading**: YOLOv8 model loaded lazily on first inference (cached globally)
   - Default path: `backend/models/best.pt`
   - Supports CPU (default) or GPU (via `YOLO_DEVICE=cuda`)
2. **Preprocessing**: YOLO automatically resizes image to 224×224 and normalizes
3. **Inference**: Model processes image, returns top-1 prediction with confidence
4. **Result**: Class name (e.g., "plastic") and confidence score (0.0-1.0)

**Model Characteristics:**
- 12 waste categories: battery, biological, brown-glass, cardboard, clothes, green-glass, metal, paper, plastic, shoes, trash, white-glass
- Input: RGB image (any size, auto-resized)
- Output: Single class prediction with confidence

#### Phase 3: Robot Sorting

**Class Mapping:**
- ML predictions mapped to 5 physical bins:
  - `paper` → paper bin
  - `plastic` → plastic bin
  - `brown-glass`, `green-glass`, `white-glass` → glass bin
  - `biological` → biological bin
  - All others → trash bin

**Robot Sequence (9 Steps):**
1. Move above pickup position (gripper open)
2. Descend to pickup height (gripper open)
3. Close gripper (pick item)
4. Lift item up (gripper closed)
5. Move above target bin (gripper closed)
6. Descend to bin height (gripper closed)
7. Open gripper (place item)
8. Lift up (gripper open)
9. Return to home position (gripper open)

**Connection Management:**
- Singleton pattern ensures single robot connection
- Auto-connects if not connected (auto-detects COM port on Windows)
- All movements are **blocking** (wait for completion before next command)

**Coordinate System:**
- Positions defined in millimeters: (x, y, z, rotation)
- Bin positions, pickup position, and home position must be manually calibrated
- Height offsets (`PICK_HEIGHT_OFFSET`, `PLACE_HEIGHT_OFFSET`) control descent depth

#### Phase 4: Response & Display

**Backend Response:**
```json
{
  "success": true,
  "saved_as": "frame_20241121_143022_456.jpg",
  "prediction": "plastic",
  "confidence": 0.95,
  "robot_action": "Sorted to PLASTIC bin"
}
```

**Frontend Display:**
- Shows prediction class and confidence percentage
- Preview automatically resumes

### Explicit Analysis of Behavior and Limitations

#### What Works Well

**1. Single Frame Capture Architecture**
- **Why it works**: DroidCam Free limitation (single connection) is handled gracefully
- **Implementation**: Preview pause/resume mechanism ensures reliable frame extraction
- **Result**: Consistent frame capture without stream conflicts

**2. Lazy Model Loading**
- **Why it works**: Model loaded only on first inference, then cached globally
- **Implementation**: Global `_model` variable prevents redundant loading
- **Result**: Fast subsequent inferences, reduced memory overhead

**3. Blocking Robot Control**
- **Why it works**: Ensures sequential execution of movements
- **Implementation**: Each `move_to()` command waits for completion
- **Result**: Predictable robot behavior, no race conditions

**4. JPEG Frame Extraction**
- **Why it works**: MJPEG format allows frame-by-frame extraction
- **Implementation**: Byte-by-byte parsing until SOI/EOI markers found
- **Result**: Reliable single-frame extraction from continuous stream

#### What Does Not Work as Expected

**1. No Continuous Video Processing**
- **Current behavior**: Processes only single frames on user click
- **Why this limitation exists**:
  - DroidCam Free allows only one connection to `/video` stream
  - Preview and processing cannot run simultaneously
  - Would require DroidCam Pro (paid) or different camera solution
- **Technical constraint**: DroidCam server architecture limitation, not our code
- **Impact**: Cannot perform real-time continuous classification/object detection

**2. No Confidence Threshold**
- **Current behavior**: Robot sorts items regardless of confidence score
- **Why this limitation exists**: No threshold check implemented in `camera_service.py`
- **Technical reality**: Prediction confidence is returned but not used for decision-making
- **Impact**: Low-confidence predictions still trigger robot action (potential misclassification)

**3. Synchronous Robot Operations**
- **Current behavior**: API response blocked until robot completes entire sequence (~10-15 seconds)
- **Why this limitation exists**: Dobot SDK uses blocking commands (`SetPTPCmd` waits for completion)
- **Technical constraint**: SDK architecture, not our implementation choice
- **Impact**: Frontend waits for full robot sequence before showing results

**4. Manual Coordinate Calibration Required**
- **Current behavior**: Bin positions must be manually measured and configured
- **Why this limitation exists**: No automatic calibration or vision-based positioning
- **Technical reality**: Coordinates hardcoded in `dobot_service.py` (lines 32-38, 95, 100)
- **Impact**: Setup requires physical measurement and code modification for each environment

**5. No Error Recovery**
- **Current behavior**: If robot fails mid-sequence, no automatic retry
- **Why this limitation exists**: No retry logic or state recovery implemented
- **Technical reality**: Errors logged but operation aborted
- **Impact**: Manual intervention required if robot fails

**6. Single Camera Stream Limitation**
- **Current behavior**: Preview must pause for capture
- **Why this limitation exists**: DroidCam Free server architecture
- **Technical constraint**: Server only accepts one TCP connection to `/video` endpoint
- **Workaround**: 250ms delay between pause and capture to ensure stream release
- **Impact**: Brief preview interruption during capture

#### Engineering Trade-offs and Constraints

**1. Frame-by-Frame vs. Continuous Processing**
- **Trade-off**: Chose single-frame extraction over continuous processing
- **Reason**: DroidCam Free limitation, cost constraints (avoiding paid DroidCam Pro)
- **Alternative considered**: USB camera with OpenCV (requires physical camera hardware)
- **Decision**: Accept single-frame limitation for cost-effective phone camera solution

**2. Blocking vs. Asynchronous Robot Control**
- **Trade-off**: Chose blocking operations for simplicity and reliability
- **Reason**: Dobot SDK provides blocking API, async wrapper would add complexity
- **Alternative considered**: Background task queue (Celery) for async robot control
- **Decision**: Keep synchronous for MVP, accept API blocking as acceptable trade-off

**3. No Confidence Threshold**
- **Trade-off**: Immediate robot action vs. user confirmation
- **Reason**: Focus on automation, threshold tuning would require extensive testing
- **Alternative considered**: Configurable threshold, manual confirmation mode
- **Decision**: Defer to future work, prioritize end-to-end pipeline completion

**4. Manual Calibration vs. Automatic Positioning**
- **Trade-off**: Simple hardcoded coordinates vs. vision-based calibration
- **Reason**: Vision-based calibration requires additional CV algorithms and testing
- **Alternative considered**: ARUco markers for automatic bin detection
- **Decision**: Manual calibration acceptable for controlled environment

### Data Flow Summary

```
DroidCam (Phone) 
  → MJPEG Stream (http://{ip}:4747/video)
    → Frontend Preview (paused during capture)
    → Backend Snapshot Service (extracts single JPEG frame)
      → Frontend Upload (FormData)
        → Backend Camera Service
          → PIL Image (RGB)
            → YOLOv8 Model (inference)
              → Prediction + Confidence
                → Dobot Service (class mapping)
                  → Robot Movement Sequence (9 steps)
                    → Response JSON
                      → Frontend Display
```

---

## 4. Outlook and Conclusion

### Key Results

**Successfully Implemented:**
- Complete end-to-end pipeline from image capture to robot sorting
- Reliable single-frame extraction from DroidCam MJPEG stream
- YOLOv8 classification with 12 waste categories
- Automated robot sorting with 9-step movement sequence
- Web-based user interface with real-time feedback

**System Capabilities:**
- Processes waste items on-demand (user-triggered)
- Classifies items into 12 categories
- Automatically sorts items into 5 physical bins
- Saves all captured frames for analysis

### Remaining Challenges and Limitations

**1. DroidCam Connection Limitation**
- Single connection constraint prevents continuous processing
- Requires preview pause/resume workaround
- **Solution**: Upgrade to DroidCam Pro or use USB camera with OpenCV

**2. No Confidence Threshold**
- Low-confidence predictions still trigger robot action
- Risk of misclassification and incorrect sorting
- **Solution**: Add configurable confidence threshold (e.g., 0.7) before robot action

**3. Synchronous Robot Operations**
- API blocks for 10-15 seconds during robot sequence
- Poor user experience during long operations
- **Solution**: Implement background task queue (Celery) with WebSocket status updates

**4. Manual Coordinate Calibration**
- Requires physical measurement and code modification
- Not portable across different setups
- **Solution**: Implement ARUco marker-based automatic calibration

**5. No Error Recovery**
- Robot failures require manual intervention
- No automatic retry or state recovery
- **Solution**: Add retry logic with exponential backoff, implement state machine

### Realistic Future Extensions

**Short-term Improvements:**
1. **Confidence Threshold**: Add threshold check before robot action
2. **Manual Confirmation Mode**: Optional user review before robot execution
3. **Better Error Handling**: Retry logic for transient robot failures
4. **Coordinate Calibration UI**: Web interface for adjusting bin positions

**Medium-term Enhancements:**
1. **Asynchronous Robot Control**: Background tasks with status updates via WebSocket
2. **Multiple Camera Support**: Support for multiple DroidCam streams
3. **Batch Processing**: Process multiple items in sequence
4. **Statistics Dashboard**: Track sorting accuracy, item counts per category

**Long-term Extensions:**
1. **Vision-Based Calibration**: Automatic bin detection using ARUco markers
2. **Real-time Continuous Processing**: Upgrade to DroidCam Pro or USB camera
3. **Multi-Robot Support**: Coordinate multiple robot arms for parallel sorting
4. **Learning from Feedback**: User correction system to improve model accuracy

### Technical Grounding

All proposed improvements are based on:
- **Existing codebase structure**: Services are modular, easy to extend
- **Available libraries**: Celery for async tasks, WebSocket support in FastAPI
- **Proven techniques**: ARUco markers widely used in robotics, confidence thresholds standard in ML
- **Hardware capabilities**: Dobot SDK supports all required movements, DroidCam Pro supports multiple streams

### Conclusion

This project successfully demonstrates a complete integration of computer vision, machine learning, and robotics for automated waste sorting. The system works reliably within its constraints, processing single frames and executing robot sorting sequences as designed.

The main limitations stem from:
- **DroidCam Free architecture** (single connection constraint)
- **Dobot SDK design** (blocking operations)
- **MVP scope** (prioritized end-to-end pipeline over advanced features)

These are **engineering trade-offs**, not failures. The system provides a solid foundation for future enhancements, with clear paths for improvement based on realistic technical solutions.

---

## Suggested Slide Breakdown

### Slide 1: Title Slide
- Project name: Smart Waste Sorter
- Course: Applied Robotics / Computer Vision
- Presenter name(s)

### Slide 2: Introduction
- Project topic overview
- Project goal (3 bullet points)
- Problem statement

### Slide 3: System Overview
- High-level architecture diagram
- Hardware components (DroidCam, Dobot, Computer)
- Software stack (Next.js, FastAPI, YOLOv8)

### Slide 4: Essential Theory - YOLOv8
- What it is (1 sentence)
- How it works (3 bullet points: input → CNN → output)
- Why we chose it (2 bullet points)

### Slide 5: Essential Theory - MJPEG & Robot Control
- MJPEG streaming (SOI/EOI markers)
- Robot control basics (position-based, blocking)
- Keep concise, visual diagram if possible

### Slide 6: Complete Pipeline Overview
- Flow diagram: Camera → Capture → ML → Robot → Response
- 4 phases labeled clearly

### Slide 7: Phase 1 - Image Capture (Detailed)
- User action flow
- Preview pause mechanism
- Frame extraction process
- **Highlight**: DroidCam single-connection limitation

### Slide 8: Phase 2 - ML Inference
- Upload process
- Model loading (lazy, cached)
- Inference workflow
- Output format

### Slide 9: Phase 3 - Robot Sorting
- Class mapping (12 → 5 bins)
- 9-step sequence (visual diagram)
- Connection management

### Slide 10: What Works Well
- 4 key successes with brief explanations
- Visual indicators (checkmarks)

### Slide 11: Limitations - DroidCam & Processing
- Single frame limitation (why, impact)
- No continuous processing (technical constraint)
- Frame as engineering trade-off

### Slide 12: Limitations - Robot & Calibration
- No confidence threshold (current behavior, impact)
- Synchronous operations (blocking, user experience)
- Manual calibration requirement

### Slide 13: Engineering Trade-offs
- 4 main trade-offs with reasoning
- Alternatives considered
- Decisions made

### Slide 14: Key Results
- Successfully implemented (4-5 items)
- System capabilities summary

### Slide 15: Remaining Challenges
- 5 main limitations
- Brief impact statements

### Slide 16: Future Extensions
- Short-term (4 items)
- Medium-term (4 items)
- Long-term (4 items)
- Technical grounding note

### Slide 17: Conclusion
- Summary of achievements
- Acknowledgment of limitations as trade-offs
- Foundation for future work

### Slide 18: Q&A
- Contact information
- Repository link (if applicable)

**Total: ~18 slides for a 15-20 minute presentation**

**Timing Suggestions:**
- Introduction: 2 minutes
- Theory: 3 minutes
- Implementation: 8-10 minutes (main focus)
- Limitations & Trade-offs: 3-4 minutes
- Outlook & Conclusion: 2-3 minutes
- Q&A: 5 minutes
