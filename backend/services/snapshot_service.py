"""
Snapshot service for extracting single frames from DroidCam MJPEG stream.
"""
import httpx

# JPEG markers
JPEG_START = b'\xff\xd8'  # Start of Image (SOI) FF D8
JPEG_END = b'\xff\xd9'    # End of Image (EOI) FF D9

# Safety limits
MAX_FRAME_BYTES = 1_500_000  # ~1.5 MB cap to avoid runaway buffering
CHUNK_SIZE = 4096


async def extract_single_frame(ip: str, timeout: float = 10.0) -> bytes:
    """
    Extract a single JPEG frame from DroidCam MJPEG stream.
    
    Args:
        ip: DroidCam IP address
        timeout: Request timeout in seconds
        
    Returns:
        JPEG image bytes
        
    Raises:
        ValueError: If IP is invalid
        ConnectionError: If connection fails
        TimeoutError: If request times out
        RuntimeError: If no JPEG frame found in stream
    """
    if not ip or not ip.strip():
        raise ValueError("IP address is required")
    
    ip = ip.strip()
    stream_url = f"http://{ip}:4747/video"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("GET", stream_url) as response:
                if response.status_code != 200:
                    raise ConnectionError(
                        f"Failed to connect to DroidCam: {response.status_code}"
                    )
                
                # Read stream byte-by-byte until we find JPEG markers
                buffer = bytearray()
                found_start = False
                
                async for chunk in response.aiter_bytes(CHUNK_SIZE):
                    buffer.extend(chunk)
                    
                    # Safety cap to avoid runaway buffering on bad streams
                    if len(buffer) > MAX_FRAME_BYTES:
                        raise RuntimeError(
                            "Frame too large or stream not providing a valid JPEG (exceeded size limit)"
                        )
                    
                    # Look for JPEG start marker
                    if not found_start:
                        start_idx = buffer.find(JPEG_START)
                        if start_idx != -1:
                            found_start = True
                            # Keep only bytes from start marker onwards
                            buffer = bytearray(buffer[start_idx:])
                    
                    # Look for JPEG end marker
                    if found_start:
                        end_idx = buffer.find(JPEG_END)
                        if end_idx != -1:
                            # Extract complete JPEG frame (including end marker)
                            jpeg_bytes = bytes(buffer[:end_idx + 2])
                            return jpeg_bytes
                
                # If we get here, we didn't find a complete frame
                if found_start:
                    raise RuntimeError(
                        "Incomplete JPEG frame: found start marker but not end marker"
                    )
                else:
                    raise RuntimeError(
                        "No JPEG frame found in stream: start marker not detected"
                    )
                    
    except httpx.TimeoutException as e:
        raise TimeoutError(f"Request to DroidCam timed out: {e}")
    except httpx.ConnectError as e:
        raise ConnectionError(f"Failed to connect to DroidCam at {ip}:4747: {e}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error extracting frame: {e}")

