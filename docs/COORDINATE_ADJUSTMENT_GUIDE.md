# Coordinate Adjustment Guide

This guide explains how to calibrate the robot coordinates for your specific physical setup.

## Coordinate System

All coordinates are defined at the top of `backend/services/dobot_service.py`. The coordinate system uses millimeters (mm) for position and degrees for rotation.

### Coordinate Format

Coordinates are specified as (x, y, z, r):
- x: Forward/backward position from robot base in millimeters
- y: Left/right position from robot base in millimeters (negative = left, positive = right)
- z: Up/down height in millimeters (negative = lower, positive = higher)
- r: Rotation angle in degrees

### Unit Conversion

Important conversion for physical measurements:
- 1 centimeter (cm) is approximately 16.7 Dobot units in X and Y axes
- Z axis and rotation use standard millimeter and degree measurements

Example: If the bin is 10 cm to the right from the robot base center, set y = 10 * 16.7 = 167 mm

## Current Coordinate Configuration

These are the coordinates currently implemented in the project. Adjust them to match the physical setup.

### Bin Positions

```python
BIN_POSITIONS = {
    "paper": (200, -15, 70, 0),
    "plastic": (200, -115, 70, 0),
    "cardboard": (200, -70, 70, 0),
    "biological": (200, 60, 70, 0),
    "trash": (200, 100, 70, 0),
}
```

Each bin position represents where the gripper will be positioned when placing items. The gripper is closed when the robot arrives at the bin position, then opens to release the object.

### Pickup Position

```python
PICKUP_POSITION = (118, -220, 100, 0)
PICK_HEIGHT_OFFSET = -44
```

The pickup position is where items are placed for the robot to pick up. The gripper is open when the robot arrives, then closes to grip the object. The PICK_HEIGHT_OFFSET determines how far below the base pickup Z position the robot descends to actually grip the object.

With the current settings:
- Base pickup position: Z = 100 mm
- Actual pickup height: 100 + (-44) = 56 mm above base level

### Home Position

```python
HOME_POSITION = (200, 0, 90, 0)
```

The home position is a safe resting position where the robot waits between operations. The gripper is always open at the home position.

### Place Height Offset

```python
PLACE_HEIGHT_OFFSET = -18
```

This offset determines how far below the bin's base Z position the robot descends when placing items. The gripper is still closed at this position, then opens to release the object.

## Safe Position Boundaries

The robot has built-in safety boundaries to prevent it from reaching dangerous positions. These limits are automatically checked before any movement:

- X-axis: 0 to 300 mm (forward from base)
- Y-axis: -300 to 200 mm (left to right from base center)
- Z-axis: -50 to 200 mm (below to above base level)
- Rotation: -180 to 180 degrees

If you try to set coordinates outside these boundaries, the movement will be blocked and an error message will be displayed.

## Complete Sorting Sequence

The robot follows a nine-step sequence during sorting operations:

1. Move above pickup position (gripper: OPEN)
   - Position: (pickup_x, pickup_y, pickup_z + 20, pickup_r)

2. Descend to pickup position (gripper: OPEN)
   - Position: (pickup_x, pickup_y, pickup_z + PICK_HEIGHT_OFFSET, pickup_r)
   - This is where the gripper will close

3. Close gripper to pick up object (gripper: CLOSES)
   - Action: pick() is called
   - Object is now gripped

4. Lift object up (gripper: CLOSED)
   - Position: (pickup_x, pickup_y, pickup_z + 20, pickup_r)

5. Move above bin position (gripper: CLOSED)
   - Position: (bin_x, bin_y, bin_z + 20, bin_r)

6. Descend to bin position (gripper: CLOSED)
   - Position: (bin_x, bin_y, bin_z + PLACE_HEIGHT_OFFSET, bin_r)
   - This is where the gripper will open

7. Open gripper to place object (gripper: OPENS)
   - Action: place() is called
   - Object is released

8. Lift up (gripper: OPEN)
   - Position: (bin_x, bin_y, bin_z + 20, bin_r)

9. Return to home position (gripper: OPEN)
   - Position: HOME_POSITION

## Calibration Process

### Step 1: Test Home Position

Start by testing and adjusting the home position. This should be a safe, clear position where the robot can rest without interfering with operations.

```python
HOME_POSITION = (200, 0, 90, 0)
```

Test by calling the home() function and verify the robot moves to a safe resting position.

### Step 2: Calibrate Pickup Position

Place an item at a known location in the physical setup. Manually move the robot to that position using the Dobot software or by reading current coordinates. Update the pickup position with those values.

```python
PICKUP_POSITION = (118, -220, 100, 0)
```

The Z coordinate should be set to a position where the gripper can safely move above the item. The actual pickup height is determined by PICK_HEIGHT_OFFSET.

### Step 3: Adjust Pick Height Offset

The pick height offset fine-tunes how far the robot descends to grip objects. Test with a sample item and adjust as needed:

- If the gripper doesn't reach the object, make the offset more negative (e.g., change from -44 to -50)
- If the gripper goes too low, make it less negative (e.g., change from -44 to -40)

The final pickup Z position is: pickup_z + PICK_HEIGHT_OFFSET

### Step 4: Calibrate Bin Positions

For each bin, manually position the robot above the center of where items should be placed. Record the (x, y, z, r) coordinates and update the corresponding bin position in BIN_POSITIONS.

The current configuration shows all bins at x=200 mm and z=70 mm, with different y positions:
- Paper: y = -15 mm (slightly left)
- Plastic: y = -115 mm (further left)
- Cardboard: y = -70 mm (middle-left)
- Biological: y = 60 mm (right)
- Trash: y = 100 mm (further right)

### Step 5: Adjust Place Height Offset

Similar to pick height, the place height offset determines how far the robot descends into the bin when placing items. Adjust this to ensure items are placed at the right depth without the gripper hitting the bin bottom.

The final place Z position is: bin_z + PLACE_HEIGHT_OFFSET

## Gripper State Reference

During the sorting sequence, the gripper state changes as follows:

| Step | Position | Gripper State | Action |
|------|----------|---------------|--------|
| 1 | Above pickup | OPEN | Move to pickup area |
| 2 | At pickup level | OPEN | Descend to object |
| 3 | At pickup level | CLOSES | Close gripper (PICK) |
| 4 | Above pickup | CLOSED | Lift object |
| 5 | Above bin | CLOSED | Move to bin |
| 6 | At bin level | CLOSED | Descend to bin |
| 7 | At bin level | OPENS | Open gripper (PLACE) |
| 8 | Above bin | OPEN | Lift up |
| 9 | Home | OPEN | Return home |

## Important Notes

- The gripper is open by default and only closes when pick() is called
- The gripper stays closed from step 3 until step 7 (holding the object)
- Height offsets are relative values added to the base Z position
- All coordinates are in millimeters, use precise measurements
- Test each position manually before running automatic sorting
- Always ensure coordinates are within the safe boundaries listed above

## Code Locations

All coordinate settings are in `backend/services/dobot_service.py`:

- Lines 32-38: BIN_POSITIONS dictionary
- Line 57: PICKUP_POSITION
- Line 58: PICK_HEIGHT_OFFSET
- Line 59: PLACE_HEIGHT_OFFSET
- Line 70: HOME_POSITION
- Lines 82-89: Safe position boundaries

Gripper control functions:
- Line 414: pick() - Closes gripper
- Line 492: place() - Opens gripper

## Calibration Tips

Start with small incremental movements when testing coordinates. Use manual control to position the robot and record working coordinates as they are found. Test height offsets separately, adjusting pick and place heights independently. Always verify the gripper has enough clearance to open and close at each position.

If issues occur, check the backend console for detailed error messages. The robot will not move if coordinates are outside safe boundaries, and an error message will explain which coordinate is invalid.
