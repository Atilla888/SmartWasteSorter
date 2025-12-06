"""
FastAPI backend for Smart Waste Sorter.
"""
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
        raise HTTPException(status_code=400, detail=str(e))
    except (ConnectionError, TimeoutError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/capture")
async def capture_frame(file: UploadFile = File(...)):
    """
    Capture and process a frame from the camera stream.
    
    Content-Type: multipart/form-data
    Body: file: <uploaded image blob>
    
    Returns:
        JSON response with success status, saved filename, prediction, and confidence.
        Example:
        {
            "success": true,
            "saved_as": "frame_20241121_143022_456.jpg",
            "prediction": "plastic",
            "confidence": 0.95
        }
    """
    try:
        result = process_frame(file)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

