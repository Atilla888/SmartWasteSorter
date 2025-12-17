"""
Camera service for processing captured frames.
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image
from fastapi import UploadFile
from ultralytics import YOLO

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import with fallback for different run contexts
try:
    from backend.utils.image_utils import read_upload_image
    from backend.services.dobot_service import sort_with_robot
except ImportError:
    # Fallback when running from backend/ directory
    from utils.image_utils import read_upload_image
    from services.dobot_service import sort_with_robot


# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent.parent
FRAMES_DIR = BASE_DIR / "frames"

# Global model instance (loaded once on first use)
_model: Optional[YOLO] = None

# Model path: use original location or env override
# Default location: backend/models/best.pt
# Can override with YOLO_MODEL_PATH environment variable
model_path_str = os.getenv("YOLO_MODEL_PATH")
if model_path_str:
    MODEL_PATH = Path(model_path_str)
else:
    # Original path: backend/models/best.pt
    MODEL_PATH = BASE_DIR / "models" / "best.pt"

# Optional: choose device (cpu by default; set CUDA via env if available)
MODEL_DEVICE = os.getenv("YOLO_DEVICE", "cpu")


def _load_model() -> YOLO:
    """
    Load the YOLO classification model globally (lazy loading).
    Model is loaded once and reused for all inference requests.
    """
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Please ensure the model is trained first."
            )
        _model = YOLO(str(MODEL_PATH), task="classify")
    return _model


def ensure_frames_directory():
    """Ensure the frames directory exists."""
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)


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
        
        # Ensure image is RGB (YOLO handles resizing to 224x224 internally)
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Run inference (YOLO handles resizing automatically)
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
        dict with success status, saved filename, prediction, confidence, and robot_action.
        Example:
        {
            "success": True,
            "saved_as": "frame_20241121_143022_456.jpg",
            "prediction": "plastic",
            "confidence": 0.95,
            "robot_action": "Sorted to PLASTIC bin"
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
        
        # Trigger robot sorting based on prediction
        print(f"\n{'='*60}")
        print(f"TRIGGERING ROBOT SORTING for prediction: {inference_result['prediction']}")
        print(f"{'='*60}")
        try:
            robot_success, robot_message = sort_with_robot(inference_result["prediction"])
            print(f"Robot operation completed: success={robot_success}, message={robot_message}")
        except Exception as e:
            print(f"ERROR: Exception during robot sorting: {e}")
            import traceback
            traceback.print_exc()
            robot_success = False
            robot_message = f"Exception: {str(e)}"
        print(f"{'='*60}\n")
        
        # Build response
        response = {
            "success": True,
            "saved_as": filename,
            "prediction": inference_result["prediction"],
            "confidence": inference_result["confidence"]
        }
        
        # Add robot action status (even if robot failed, we still return the prediction)
        if robot_success:
            response["robot_action"] = robot_message
        else:
            response["robot_action"] = f"Robot error: {robot_message}"
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

