"""
FastAPI backend for Smart Waste Sorter.
"""
import os
import sys
from pathlib import Path

# Add project root to path to allow imports when running from backend/
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

# Import with fallback for different run contexts
try:
    from backend.services.camera_service import process_frame
    from backend.services.snapshot_service import extract_single_frame
except ImportError:
    # Fallback when running from backend/ directory
    from services.camera_service import process_frame
    from services.snapshot_service import extract_single_frame


def validate_environment():
    """
    Validate environment variables at startup.
    Prints warnings for optional variables and errors for critical missing ones.
    """
    # Critical environment variables (will fail if missing)
    critical_vars = {}
    
    # Optional but recommended environment variables
    optional_vars = {
        "YOLO_MODEL_PATH": "Path to YOLO model file (defaults to backend/models/best.pt)",
        "YOLO_DEVICE": "Device for YOLO inference: 'cpu' or 'cuda' (defaults to 'cpu')",
        "MAX_FILE_SIZE": "Maximum file size in bytes (defaults to 10MB)",
        "FASTAPI_URL": "FastAPI backend URL (used by frontend, defaults to http://localhost:8000)"
    }
    
    # Check critical variables
    missing_critical = []
    for var_name, description in critical_vars.items():
        if not os.getenv(var_name):
            missing_critical.append(f"{var_name}: {description}")
    
    if missing_critical:
        error_msg = "Missing required environment variables:\n" + "\n".join(f"  - {var}" for var in missing_critical)
        print(f"ERROR: {error_msg}")
        raise ValueError(error_msg)
    
    # Check optional variables and print warnings
    missing_optional = []
    for var_name, description in optional_vars.items():
        if not os.getenv(var_name):
            missing_optional.append(f"{var_name}: {description}")
    
    if missing_optional:
        print("WARNING: Optional environment variables not set (using defaults):")
        for var in missing_optional:
            print(f"  - {var}")
    
    # Validate format of set variables
    if os.getenv("MAX_FILE_SIZE"):
        try:
            max_size = int(os.getenv("MAX_FILE_SIZE"))
            if max_size <= 0:
                print(f"WARNING: MAX_FILE_SIZE must be positive, got {max_size}. Using default 10MB.")
        except ValueError:
            print(f"WARNING: MAX_FILE_SIZE must be an integer, got '{os.getenv('MAX_FILE_SIZE')}'. Using default 10MB.")
    
    if os.getenv("YOLO_DEVICE"):
        device = os.getenv("YOLO_DEVICE").lower()
        if device not in ["cpu", "cuda"]:
            print(f"WARNING: YOLO_DEVICE should be 'cpu' or 'cuda', got '{device}'. Using 'cpu'.")
    
    print("✓ Environment variable validation completed.")


# Validate environment on import
try:
    validate_environment()
except ValueError as e:
    print(f"ERROR: {e}")
    print("Please set the required environment variables before starting the server.")
    sys.exit(1)

app = FastAPI(title="Smart Waste Sorter API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"message": "Smart Waste Sorter API is running"}


@app.get("/snapshot")
async def snapshot(ip: str = Query(..., description="DroidCam IP address")):
    """
    Extract a single JPEG frame from DroidCam MJPEG stream.
    
    Query parameters:
        ip: DroidCam IP address (e.g., 192.168.0.105)
    
    Returns:
        JPEG image bytes with content-type: image/jpeg
    """
    try:
        jpeg_bytes = await extract_single_frame(ip)
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except ValueError as e:
        error_msg = str(e)
        if "IP address" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid IP address: {error_msg}. Please provide a valid IP address (e.g., 192.168.0.105)."
            )
        raise HTTPException(status_code=400, detail=error_msg)
    except ConnectionError as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to DroidCam camera: {error_msg}. Please check: 1) Camera is powered on, 2) IP address is correct, 3) Camera and computer are on the same network, 4) DroidCam app is running."
        )
    except TimeoutError as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=503,
            detail=f"Request to camera timed out: {error_msg}. The camera may be busy or unreachable. Please try again."
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "JPEG" in error_msg or "frame" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract frame from camera stream: {error_msg}. The camera stream may be corrupted or unavailable."
            )
        raise HTTPException(status_code=500, detail=f"Processing error: {error_msg}")
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error occurred: {error_msg}. Please try again or contact support if the issue persists."
        )


@app.post("/capture")
async def capture_frame(file: UploadFile = File(...)):
    """
    Capture and process a frame from the camera stream.
    
    Content-Type: multipart/form-data
    Body: file: <uploaded image blob>
    
    Returns:
        JSON response with success status, saved filename, prediction, confidence, and robot_action.
        Example:
        {
            "success": true,
            "saved_as": "frame_20241121_143022_456.jpg",
            "prediction": "plastic",
            "confidence": 0.95,
            "robot_action": "Sorted to PLASTIC bin"
        }
    """
    try:
        result = process_frame(file)
        return result
    except Exception as e:
        error_msg = str(e)
        if not error_msg:
            error_msg = "An unexpected error occurred during image processing."
        return {
            "success": False,
            "error": f"Processing failed: {error_msg}. Please ensure the image is valid and try again."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

