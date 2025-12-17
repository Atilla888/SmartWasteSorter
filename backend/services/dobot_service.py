"""
Dobot Magician robot control service using Official Dobot SDK.

Provides singleton connection management and movement control for the Dobot robotic arm.
Uses DobotDllType.py and DobotDll.dll from backend/dobot_magician/.
All movements are blocking (wait until completion).
"""
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# Add dobot_magician directory to Python path
backend_dir = Path(__file__).parent.parent
dobot_dir = backend_dir / "dobot_magician"
if str(dobot_dir) not in sys.path:
    sys.path.insert(0, str(dobot_dir))

# Try to import Dobot SDK
try:
    import DobotDllType as dType
    DOBOT_AVAILABLE = True
except ImportError as e:
    DOBOT_AVAILABLE = False
    print(f"Dobot SDK import error: {e}")
    print("Please ensure DobotDllType.py and DobotDll.dll are in backend/dobot_magician/")

# Bin positions mapping (x, y, z, r) in millimeters
# Only 5 bins: paper, plastic, glass, biological, and trash (for all other classes)
# ADJUST THESE: Set the exact coordinates where each bin is located
# Gripper will be CLOSED when robot arrives at bin, then OPENS to release object
BIN_POSITIONS = {
    "paper": (187, 110, 50, 0),  # z-40          # Paper bin - ADJUST ME!
    "plastic": (91, 110, 50, 0),            # Plastic bin - ADJUST ME!
    "glass": (0, 150, 50, 0),           # Glass bin - ADJUST ME!
    "biological": (0, 190, 50, 0),       # Biological waste bin - ADJUST ME!
    "trash": (0, 230, 50, 0),              # General trash bin - ADJUST ME!
}

# Mapping function: converts ML prediction classes to robot bin classes
# Only handles: paper, plastic, glass, biological
# All other classes → "trash"
def map_class_to_bin(ml_prediction: str) -> str:
    """
    Map ML prediction class to robot bin class.
    
    Only specific classes are handled:
    - paper → paper
    - plastic → plastic
    - brown-glass, green-glass, white-glass → glass
    - biological → biological
    - All others → trash
    
    Args:
        ml_prediction: ML model prediction class name
        
    Returns:
        Robot bin class name: "paper", "plastic", "glass", "biological", or "trash"
    """
    ml_prediction_lower = ml_prediction.lower().strip()
    
    # Direct matches
    if ml_prediction_lower == "paper":
        return "paper"
    elif ml_prediction_lower == "plastic":
        return "plastic"
    elif ml_prediction_lower == "biological":
        return "biological"
    
    # Glass variations → "glass"
    elif ml_prediction_lower in ["brown-glass", "green-glass", "white-glass", "glass"]:
        return "glass"
    
    # All other classes → "trash"
    else:
        return "trash"

# ============================================================================
# COORDINATE CALIBRATION SECTION
# ============================================================================
# Adjust these coordinates to match your physical setup.
# All coordinates are in millimeters (mm).
# Format: (x, y, z, r) where:
#   - x: Forward/backward from robot base (mm)
#   - y: Left/right from robot base (mm)
#   - z: Up/down height (mm, negative = lower, positive = higher)
#   - r: Rotation angle (degrees)
#
# See COORDINATE_ADJUSTMENT_GUIDE.md for detailed explanation.
# ============================================================================

# Pickup position (where items are placed for sorting)
# ADJUST THIS: Position where you place items for the robot to pick up
# Gripper will be OPEN when robot arrives here, then CLOSES to pick object
PICKUP_POSITION = (250, -135, 90, 0)  # (x, y, z, r) - ADJUST ME!
PICK_HEIGHT_OFFSET = -20
PLACE_HEIGHT_OFFSET = -10
# Home position (safe starting position - robot arm rest position)
# ADJUST THIS: Safe neutral position where robot waits between operations
# Gripper is always OPEN at home position
HOME_POSITION = (200, 0, 90, 0)  # (x, y, z, r) - ADJUST ME!

# Movement parameters
MOVE_SPEED = 200  # mm/s
MOVE_ACCELERATION = 40  # mm/s²

# Height offsets - ADJUST THESE to fine-tune pick/place heights
# How far BELOW the base position the robot goes when picking/placing
# More negative = lower (robot goes down further)
# Less negative = higher (robot doesn't go as low)
#PICK_HEIGHT_OFFSET = -40  # mm - How far down from pickup_z when picking (ADJUST ME!)
#PLACE_HEIGHT_OFFSET = -40  # mm - How far down from bin_z when placing (ADJUST ME!)


class DobotService:
    """
    Singleton service for Dobot Magician robot control using Official DLL SDK.
    
    Manages connection, movement, and sorting operations.
    All movements are blocking (wait until completion).
    """
    
    _instance: Optional['DobotService'] = None
    _api: Optional[object] = None
    _connected: bool = False
    _port: Optional[str] = None
    
    def __new__(cls):
        """Singleton pattern - only one instance exists."""
        if cls._instance is None:
            cls._instance = super(DobotService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the Dobot service."""
        if not DOBOT_AVAILABLE:
            self._connected = False
            return
        self._sorting_in_progress = False
    
    def _find_dobot_port(self) -> Optional[str]:
        """
        Automatically detect Dobot serial port by trying common ports.
        
        Returns:
            Port name (e.g., 'COM5') or None if not found
        """
        if not DOBOT_AVAILABLE:
            return None
        
        # Common Dobot port patterns (Windows)
        common_ports = ['COM5', 'COM4', 'COM3', 'COM6', 'COM7', 'COM8']
        
        # Try common ports by attempting connection
        for port in common_ports:
            try:
                # Load API and try to connect
                test_api = dType.load()
                result = dType.ConnectDobot(test_api, port, 115200)
                if result[0] == dType.DobotConnect.DobotConnect_NoError:
                    dType.DisconnectDobot(test_api)
                    return port
            except Exception:
                continue
        
        return None
    
    def connect(self, port: Optional[str] = None, baudrate: int = 115200) -> bool:
        """
        Connect to Dobot robot using Official SDK.
        
        Args:
            port: Serial port (e.g., 'COM5'). If None or empty string "", auto-detect.
            baudrate: Serial baudrate (default: 115200)
            
        Returns:
            True if connected successfully, False otherwise
        """
        if not DOBOT_AVAILABLE:
            print("Warning: Official Dobot SDK not available. Cannot connect to Dobot.")
            return False
        
        if self._connected:
            return True
        
        try:
            # Load the DLL API
            self._api = dType.load()
            
            # Auto-detect port if not provided or empty
            if not port or port == "":
                port = self._find_dobot_port()
                if port is None:
                    print("Error: Could not find Dobot port. Please specify port manually.")
                    return False
            
            # Connect to robot
            result = dType.ConnectDobot(self._api, port, baudrate)
            connect_status = result[0]
            
            if connect_status != dType.DobotConnect.DobotConnect_NoError:
                error_msg = {
                    dType.DobotConnect.DobotConnect_NotFound: "Dobot not found",
                    dType.DobotConnect.DobotConnect_Occupied: "Port occupied"
                }.get(connect_status, f"Unknown error: {connect_status}")
                print(f"Error connecting to Dobot: {error_msg}")
                self._api = None
                return False
            
            self._port = port
            self._connected = True
            
            # Clear command queue
            dType.SetQueuedCmdClear(self._api)
            dType.dSleep(200)  # Wait a bit after clearing
            
            # Set motion parameters
            dType.SetPTPJointParams(self._api, 200, 200, 200, 200, 200, 200, 200, 200, isQueued=1)
            dType.SetPTPCommonParams(self._api, 100, 100, isQueued=1)
            
            # Start executing queued commands
            dType.SetQueuedCmdStartExec(self._api)
            dType.dSleep(200)

            # -------------- NEW: REQUIRED FOR MOVEMENT ----------------
            # Run HOME immediately to activate motors and queue system
            print("Running initial HOME command...")
            home_idx = dType.SetHOMECmd(self._api, 0, 1)[0]

            # Wait for HOME to finish
            while True:
                current = dType.GetQueuedCmdCurrentIndex(self._api)[0]
                if current >= home_idx:
                    break
                dType.dSleep(100)
            
            print(f"Dobot connected successfully on port {port}")
            return True
            
        except Exception as e:
            print(f"Error connecting to Dobot: {e}")
            self._connected = False
            self._api = None
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Dobot robot."""
        if self._connected and self._api:
            try:
                # Stop executing commands
                dType.SetQueuedCmdStopExec(self._api)
                # Disconnect
                dType.DisconnectDobot(self._api)
            except Exception as e:
                print(f"Error during disconnect: {e}")
        
        self._api = None
        self._connected = False
        self._port = None
    
    def is_connected(self) -> bool:
        """Check if robot is connected."""
        return self._connected and self._api is not None
    
    def _ensure_connected(self) -> None:
        """Ensure robot is connected, raise error if not."""
        if not self.is_connected():
            raise RuntimeError("Dobot is not connected. Call connect() first.")
    
    def move_to(self, x: float, y: float, z: float, r: float = 0, wait: bool = True) -> bool:
        """
        Move robot to specified position using PTP movement.
        
        Args:
            x: X coordinate (mm)
            y: Y coordinate (mm)
            z: Z coordinate (mm)
            r: Rotation angle (degrees)
            wait: If True, wait for movement to complete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            print(f"ERROR: Dobot is not connected (attempted move to: x={x}, y={y}, z={z}, r={r})")
            return False
        
        try:
            print(f"  → Moving to: ({x:.1f}, {y:.1f}, {z:.1f}, {r:.1f})")
            
            # Use PTPMOVJXYZMode for joint movement (faster)
            # Set isQueued=1 to queue the command
            queued_index = dType.SetPTPCmd(
                self._api,
                dType.PTPMode.PTPMOVJXYZMode,
                x, y, z, r,
                isQueued=1
            )[0]
            
            if wait:
                # Wait for command to complete by polling queue index
                max_wait_time = 15.0  # Increased timeout to 15 seconds
                start_time = time.time()
                command_completed = False
                
                while time.time() - start_time < max_wait_time:
                    try:
                        current_index = dType.GetQueuedCmdCurrentIndex(self._api)[0]
                        if current_index >= queued_index:
                            # Command executed
                            command_completed = True
                            break
                    except Exception as e:
                        print(f"  Warning: Error checking command status: {e}")
                        pass
                    dType.dSleep(100)  # Sleep 100ms
                
                if not command_completed:
                    print(f"  ERROR: Movement timed out after {max_wait_time}s (queued_index={queued_index})")
                    return False
                
                # Additional small delay for stability
                dType.dSleep(300)
                print(f"  ✓ Movement completed")
            
            return True
        except Exception as e:
            print(f"  ERROR: Exception during movement to ({x}, {y}, {z}, {r}): {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def pick(self) -> bool:
        """
        Close gripper to pick up object.
        
        HOW IT WORKS:
        - The Dobot Magician has a gripper end effector (mechanical gripper)
        - This function sends a command to CLOSE the gripper
        - enableCtrl=1: Enable control of the gripper
        - on=1: Close the gripper (grip the object)
        - The robot needs to be positioned so the gripper can grasp the object
        
        Uses SetEndEffectorGripper(enableCtrl, on) from SDK.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            print("Error: Dobot is not connected")
            return False
        
        try:
            print("Closing gripper (PICK)...")
            # SetEndEffectorGripper(api, enableCtrl, on, isQueued)
            # enableCtrl=1: enable control, on=1: close gripper (grip object)
            queued_index = dType.SetEndEffectorGripper(self._api, 1, 1, isQueued=1)[0]
            
            # Wait for command to execute
            max_wait = 2.0
            start_time = time.time()
            while time.time() - start_time < max_wait:
                try:
                    current_index = dType.GetQueuedCmdCurrentIndex(self._api)[0]
                    if current_index >= queued_index:
                        break
                except Exception:
                    pass
                dType.dSleep(50)
            
            dType.dSleep(500)  # Additional wait for gripper to close completely
            print("Gripper closed (object gripped)")
            return True
        except Exception as e:
            print(f"Error picking object: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def place(self) -> bool:
        """
        Open gripper to place object.
        
        HOW IT WORKS:
        - Opens the mechanical gripper to release the object
        - enableCtrl=1: Keep control enabled
        - on=0: Open the gripper (release the object)
        - Object should drop into the bin below
        
        Uses SetEndEffectorGripper(enableCtrl, on) from SDK.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            print("Error: Dobot is not connected")
            return False
        
        try:
            print("Opening gripper (PLACE)...")
            # SetEndEffectorGripper(api, enableCtrl, on, isQueued)
            # enableCtrl=1: enable control, on=0: open gripper (release object)
            queued_index = dType.SetEndEffectorGripper(self._api, 1, 0, isQueued=1)[0]
            
            # Wait for command to execute
            max_wait = 2.0
            start_time = time.time()
            while time.time() - start_time < max_wait:
                try:
                    current_index = dType.GetQueuedCmdCurrentIndex(self._api)[0]
                    if current_index >= queued_index:
                        break
                except Exception:
                    pass
                dType.dSleep(50)
            
            dType.dSleep(500)  # Additional wait for gripper to fully open
            print("Gripper opened (object released)")
            return True
        except Exception as e:
            print(f"Error placing object: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def home(self) -> bool:
        """
        Move robot to home position using SetHOMECmd.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            print("Error: Dobot is not connected")
            return False
        
        try:
            # Use SetHOMECmd from SDK
            queued_indices = dType.SetHOMECmd(self._api, temp=0, isQueued=1)
            queued_index = queued_indices[0]  # Get first index
            
            # Wait for home command to complete
            max_wait_time = 15.0  # Home can take longer
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    current_index = dType.GetQueuedCmdCurrentIndex(self._api)[0]
                    if current_index >= queued_index:
                        break
                except Exception:
                    pass
                dType.dSleep(100)
            
            dType.dSleep(1000)  # Additional wait for stability
            return True
        except Exception as e:
            print(f"Error moving to home: {e}")
            # Fallback to manual home position
            try:
                x, y, z, r = HOME_POSITION
                return self.move_to(x, y, z, r, wait=True)
            except Exception as e2:
                print(f"Error in fallback home: {e2}")
                return False
    
    def sort_item(self, class_name: str) -> Tuple[bool, str]:
        """
        Complete sorting sequence: pick item, move to bin, place, return home.
        
        Args:
            class_name: Waste class name from ML prediction (e.g., "plastic", "brown-glass", "metal")
                       Will be mapped to bin classes: paper, plastic, glass, biological, or trash
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Prevent multiple simultaneous operations
        if self._sorting_in_progress:
            error_msg = "Sorting operation already in progress. Please wait for current operation to complete."
            print(f"ERROR: {error_msg}")
            return False, error_msg
        
        if not self.is_connected():
            print("ERROR: Dobot is not connected in sort_item()")
            return False, "Dobot is not connected"
        
        # Set flag to prevent concurrent operations
        self._sorting_in_progress = True
        
        try:
            print(f"\n{'='*50}")
            print(f"Starting sorting sequence for: {class_name}")
            print(f"{'='*50}")
            
            # Print current coordinate configuration for debugging
            print(f"\nCurrent Coordinate Configuration:")
            print(f"  PICKUP_POSITION: {PICKUP_POSITION}")
            print(f"  HOME_POSITION: {HOME_POSITION}")
            print(f"  PICK_HEIGHT_OFFSET: {PICK_HEIGHT_OFFSET}")
            print(f"  PLACE_HEIGHT_OFFSET: {PLACE_HEIGHT_OFFSET}")
            print(f"  BIN_POSITIONS:")
            for bin_name, pos in BIN_POSITIONS.items():
                print(f"    {bin_name}: {pos}")
            
            # Map ML prediction to bin class (paper, plastic, glass, biological, or trash)
            bin_class = map_class_to_bin(class_name)
            original_class = class_name  # Keep original for message
            
            print(f"\nML Prediction: {original_class}")
            print(f"Mapped to bin: {bin_class}")
            
            # Get bin position for the mapped class
            if bin_class not in BIN_POSITIONS:
                error_msg = f"Unknown bin class: {bin_class}"
                print(f"ERROR: {error_msg}")
                return False, error_msg
            
            bin_pos = BIN_POSITIONS[bin_class]
            bin_x, bin_y, bin_z, bin_r = bin_pos
            print(f"Target bin position: ({bin_x}, {bin_y}, {bin_z}, {bin_r})")
            
            # Validate coordinates are within reasonable range
            if abs(bin_x) > 300 or abs(bin_y) > 300 or bin_z > 200 or bin_z < -200:
                print(f"WARNING: Bin coordinates seem unusual (x={bin_x}, y={bin_y}, z={bin_z}, r={bin_r})")
                print(f"  Please verify these coordinates are correct for your setup.")
            
            # ============================================================
            # PICKUP PHASE - Gripper starts OPEN, then CLOSES
            # ============================================================
            
            # Step 1: Move above pickup position
            # GRIPPER STATE: OPEN ⬜
            pickup_x, pickup_y, pickup_z, pickup_r = PICKUP_POSITION
            print(f"\nStep 1/9: Moving above pickup position ({pickup_x}, {pickup_y}, {pickup_z + 20}, {pickup_r}) [Gripper: OPEN]")
            if not self.move_to(pickup_x, pickup_y, pickup_z + 20, pickup_r, wait=True):
                return False, "Failed to move to pickup position"
            
            # Step 2: Descend to pickup position (at object level)
            # GRIPPER STATE: OPEN ⬜ (about to close)
            print(f"Step 2/9: Descending to pickup position ({pickup_x}, {pickup_y}, {pickup_z + PICK_HEIGHT_OFFSET}, {pickup_r}) [Gripper: OPEN]")
            if not self.move_to(pickup_x, pickup_y, pickup_z + PICK_HEIGHT_OFFSET, pickup_r, wait=True):
                return False, "Failed to descend to pickup position"
            
            # Step 3: Pick up object - GRIPPER CLOSES HERE!
            # GRIPPER STATE: CLOSES ⬛ (picks up object)
            print("Step 3/9: Picking up object (closing gripper) [Gripper: CLOSING]")
            if not self.pick():
                return False, "Failed to pick up object"
            print("  ✓ Gripper closed - object gripped")
            
            # Step 4: Lift up with object
            # GRIPPER STATE: CLOSED ⬛ (holding object)
            print(f"Step 4/9: Lifting object up ({pickup_x}, {pickup_y}, {pickup_z + 20}, {pickup_r}) [Gripper: CLOSED]")
            if not self.move_to(pickup_x, pickup_y, pickup_z + 20, pickup_r, wait=True):
                return False, "Failed to lift object"
            
            # ============================================================
            # MOVEMENT PHASE - Gripper stays CLOSED (holding object)
            # ============================================================
            
            # Step 5: Move above bin position
            # GRIPPER STATE: CLOSED ⬛ (still holding object)
            print(f"Step 5/9: Moving above bin position ({bin_x}, {bin_y}, {bin_z + 20}, {bin_r}) [Gripper: CLOSED]")
            if not self.move_to(bin_x, bin_y, bin_z + 20, bin_r, wait=True):
                return False, "Failed to move to bin position"
            
            # Step 6: Descend to bin position
            # GRIPPER STATE: CLOSED ⬛ (still holding object, about to release)
            print(f"Step 6/9: Descending to bin position ({bin_x}, {bin_y}, {bin_z + PLACE_HEIGHT_OFFSET}, {bin_r}) [Gripper: CLOSED]")
            if not self.move_to(bin_x, bin_y, bin_z + PLACE_HEIGHT_OFFSET, bin_r, wait=True):
                return False, "Failed to descend to bin position"
            
            # ============================================================
            # PLACE PHASE - Gripper OPENS to release object
            # ============================================================
            
            # Step 7: Place object - GRIPPER OPENS HERE!
            # GRIPPER STATE: OPENS ⬜ (releases object)
            print("Step 7/9: Placing object (opening gripper) [Gripper: OPENING]")
            if not self.place():
                return False, "Failed to place object"
            print("  ✓ Gripper opened - object released")
            
            # Step 8: Lift up (gripper now empty)
            # GRIPPER STATE: OPEN ⬜ (no longer holding object)
            print(f"Step 8/9: Lifting up after placing ({bin_x}, {bin_y}, {bin_z + 20}, {bin_r}) [Gripper: OPEN]")
            if not self.move_to(bin_x, bin_y, bin_z + 20, bin_r, wait=True):
                return False, "Failed to lift after placing"
            
            # ============================================================
            # RETURN PHASE - Gripper stays OPEN (ready for next item)
            # ============================================================
            
            # Step 9: Return home
            # GRIPPER STATE: OPEN ⬜ (ready for next operation)
            print("Step 9/9: Returning to home position [Gripper: OPEN]")
            if not self.home():
                return False, "Failed to return home"
            
            # Build success message
            if bin_class == original_class.lower().strip():
                # Direct match (no mapping needed)
                message = f"Sorted to {bin_class.upper()} bin"
            else:
                # Mapped to different bin (e.g., "brown-glass" → "glass", or "metal" → "trash")
                message = f"Sorted to {bin_class.upper()} bin (predicted: {original_class})"
            
            return True, message
            
        except Exception as e:
            error_msg = f"Sorting error: {str(e)}"
            print(f"\n{'='*50}")
            print(f"ERROR: {error_msg}")
            print(f"{'='*50}\n")
            import traceback
            traceback.print_exc()
            return False, error_msg
        finally:
            # Always reset the flag, even if there was an error
            self._sorting_in_progress = False


# Global singleton instance
_dobot_service: Optional[DobotService] = None


def get_dobot_service() -> DobotService:
    """
    Get the global Dobot service instance (singleton).
    
    Returns:
        DobotService instance
    """
    global _dobot_service
    if _dobot_service is None:
        _dobot_service = DobotService()
    return _dobot_service


def sort_with_robot(class_name: str) -> Tuple[bool, str]:
    """
    Convenience function to sort an item using the robot.
    
    Args:
        class_name: Waste class name (e.g., "plastic", "metal")
        
    Returns:
        Tuple of (success: bool, message: str)
        
    Example:
        success, message = sort_with_robot("plastic")
        if success:
            print(f"Robot: {message}")
    """
    print(f"\n>>> sort_with_robot() called with class_name='{class_name}'")
    
    try:
        # Check if Dobot SDK is available FIRST
        if not DOBOT_AVAILABLE:
            error_msg = "Dobot SDK not available - check dobot_magician folder"
            print(f"ERROR: {error_msg}")
            print("  Make sure DobotDllType.py and DobotDll.dll exist in backend/dobot_magician/")
            return False, error_msg
        
        print("  ✓ Dobot SDK is available")
        
        service = get_dobot_service()
        print("  ✓ DobotService instance obtained")
        
        # Auto-connect if not connected
        if not service.is_connected():
            print("  ⚠ Robot not connected, attempting to connect...")
            if not service.connect():
                error_msg = "Failed to connect to Dobot - check USB connection and COM port"
                print(f"ERROR: {error_msg}")
                print("  Troubleshooting:")
                print("    1. Check USB cable connection")
                print("    2. Verify COM port (Windows: Device Manager -> Ports)")
                print("    3. Make sure Dobot is powered on")
                print("    4. Check if another program is using the COM port")
                return False, error_msg
            print("  ✓ Robot connected successfully")
        else:
            print("  ✓ Robot already connected")
        
        print(f"  → Calling sort_item('{class_name}')...")
        result = service.sort_item(class_name)
        
        if result[0]:
            print(f"  ✓ SUCCESS: {result[1]}")
        else:
            print(f"  ✗ FAILED: {result[1]}")
        
        print(f"<<< sort_with_robot() returning: {result}\n")
        return result
        
    except Exception as e:
        error_msg = f"Exception in sort_with_robot: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        print(f"<<< sort_with_robot() returning: (False, '{error_msg}')\n")
        return False, error_msg

