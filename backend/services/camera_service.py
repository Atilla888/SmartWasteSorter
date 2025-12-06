"""
Camera service for processing captured frames.
"""
import os
from datetime import datetime
from PIL import Image
from fastapi import UploadFile
import sys
from pathlib import Path
from ultralytics import YOLO

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

# Global model instance (loaded once on first use)
_model = None
# Model path relative to project root (one level up from backend/)
MODEL_PATH = os.path.join(str(project_root), "training", "model_output", "run", "weights", "best.pt")


def _load_model():
    """
    Load the YOLO classification model globally (lazy loading).
    Model is loaded once and reused for all inference requests.
    """
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Please ensure the model is trained first."
            )
        _model = YOLO(MODEL_PATH, task="classify")
    return _model


def ensure_frames_directory():
    """Ensure the frames directory exists."""
    os.makedirs(FRAMES_DIR, exist_ok=True)


def run_inference(image: Image.Image) -> dict:
    """
    Run YOLO classification inference on a PIL Image.
    
    Args:
        image: PIL Image in RGB format
        
    Returns:
        dict with 'prediction' (class name) and 'confidence' (0.0-1.0)
        
    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If inference fails
    """
    try:
        # Load model (lazy loading - only loads once)
        model = _load_model()
        
        # Run inference (YOLO handles resizing to 224x224 internally)
        results = model(image, verbose=False)
        
        # Get top-1 prediction
        result = results[0]
        
        # Extract class name and confidence
        # For classification, results contain probs attribute
        if hasattr(result, 'probs'):
            top1_idx = result.probs.top1
            confidence = float(result.probs.top1conf)
            class_name = result.names[top1_idx]
        else:
            # Fallback if structure is different
            raise RuntimeError("Unexpected model output format")
        
        return {
            "prediction": class_name,
            "confidence": confidence
        }
        
    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"Inference failed: {str(e)}")


def process_frame(file: UploadFile) -> dict:
    """
    Process an uploaded frame: decode, save to frames directory, and run ML inference.
    
    Args:
        file: FastAPI UploadFile object containing the image
        
    Returns:
        dict with success status, saved filename, prediction, and confidence.
        Example:
        {
            "success": True,
            "saved_as": "frame_20241121_143022_456.jpg",
            "prediction": "plastic",
            "confidence": 0.95
        }
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
        
        # Run ML inference on the saved image
        inference_result = run_inference(image)
        
        return {
            "success": True,
            "saved_as": filename,
            "prediction": inference_result["prediction"],
            "confidence": inference_result["confidence"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

