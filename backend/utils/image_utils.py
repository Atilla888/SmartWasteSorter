"""
Utility functions for image processing.
"""
from PIL import Image
from fastapi import UploadFile
from io import BytesIO


def read_upload_image(file: UploadFile) -> Image.Image:
    """
    Read uploaded file bytes and convert to PIL Image (RGB).
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        PIL Image in RGB format
    """
    # Read file bytes
    file_bytes = file.file.read()
    
    # Convert bytes to PIL Image
    image = Image.open(BytesIO(file_bytes))
    
    # Convert to RGB (handles RGBA, grayscale, etc.)
    image = image.convert("RGB")
    
    return image

