"""
Camera service for processing captured frames.
"""
import os
from datetime import datetime
from PIL import Image
from fastapi import UploadFile
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import with fallback for different run contexts
try:
    from backend.utils.image_utils import read_upload_image
except ImportError:
    # Fallback when running from backend/ directory
    from utils.image_utils import read_upload_image


# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.path.join(BASE_DIR, "frames")


def ensure_frames_directory():
    """Ensure the frames directory exists."""
    os.makedirs(FRAMES_DIR, exist_ok=True)


def process_frame(file: UploadFile) -> dict:
    """
    Process an uploaded frame: decode, save to frames directory.
    
    Args:
        file: FastAPI UploadFile object containing the image
        
    Returns:
        dict with success status and saved filename
    """
    try:
        # Ensure frames directory exists
        ensure_frames_directory()
        
        # Decode uploaded file into PIL Image (RGB)
        image = read_upload_image(file)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        filename = f"frame_{timestamp}.jpg"
        filepath = os.path.join(FRAMES_DIR, filename)
        
        # Save frame to frames directory
        image.save(filepath, "JPEG", quality=95)
        
        # TODO: run ML model here in Phase 3
        
        return {
            "success": True,
            "saved_as": filename
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

