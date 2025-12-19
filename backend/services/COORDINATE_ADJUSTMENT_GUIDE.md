# Coordinate Adjustment Guide & Gripper State Explanation

## 📍 Where to Adjust Coordinates

All coordinates are defined at the **TOP of `dobot_service.py`** (lines 28-92). Here are the exact locations:

### 1. **Bin Positions** (Lines 31-38)
```python
BIN_POSITIONS = {
    "paper": (0, 0, 0, 0),            # ← ADJUST HERE
    "plastic": (0, 0, 0, 0),            # ← ADJUST HERE
    "glass": (0, 0, 0, 0),           # ← ADJUST HERE
    "biological": (0, 0, 0, 0),       # ← ADJUST HERE
    "trash": (0, 0, 0, 0),              # ← ADJUST HERE
}
```
**Format:** `(x, y, z, r)` in millimeters
- `x`: Forward/backward position
- `y`: Left/right position  
- `z`: Up/down position (negative = lower)
- `r`: Rotation angle (degrees)

### 2. **Pickup Position** (Line 81)
```python
PICKUP_POSITION = (250, -135, 80, 0)  # ← ADJUST HERE
```
**Where items are placed for sorting** - This is where the robot picks up items.

### 3. **Home Position** (Line 86)
```python
HOME_POSITION = (200, 0, 80, 0)  # ← ADJUST HERE
```
**Safe starting/resting position** - Where robot returns after sorting.

### 4. **Height Offsets** (Lines 91-92)
```python
PICK_HEIGHT_OFFSET = -20  # ← ADJUST HERE (how far down for picking)
PLACE_HEIGHT_OFFSET = -10  # ← ADJUST HERE (how far down for placing)
```
**How far down the robot goes** from the base Z position when picking/placing.

---

## 🤖 Complete Sorting Sequence with Gripper States

Here's the **exact sequence** showing when the gripper is OPEN vs CLOSED:

```
┌─────────────────────────────────────────────────────────────┐
│                   GRIPPER STATE DIAGRAM                     │
└─────────────────────────────────────────────────────────────┘

START: Robot at HOME position
   ↓
   GRIPPER STATE: OPEN
   
   ┌─────────────────────────────────────────────┐
   │ STEP 1: Move above pickup position          │
   │ Position: (pickup_x, pickup_y, pickup_z+20) │
   │ Gripper: OPEN                               │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 2: Descend to pickup position          │
   │ Position: (pickup_x, pickup_y,              │
   │            pickup_z + PICK_HEIGHT_OFFSET)   │
   │ Gripper: OPEN                               │
   │ NOTE: Robot now at object level             │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 3: PICK - Close gripper                │
   │ Action: pick() → Gripper CLOSES             │
   │ Gripper: CLOSED                             │
   │ NOTE: Object is now gripped!                │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 4: Lift object up                      │
   │ Position: (pickup_x, pickup_y, pickup_z+20) │
   │ Gripper: CLOSED                             │
   │ NOTE: Object is held while moving           │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 5: Move above bin position             │
   │ Position: (bin_x, bin_y, bin_z+20)          │
   │ Gripper: CLOSED                             │
   │ NOTE: Object still gripped                  │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 6: Descend to bin position             │
   │ Position: (bin_x, bin_y,                    │
   │            bin_z + PLACE_HEIGHT_OFFSET)     │
   │ Gripper: CLOSED                             │
   │ NOTE: Object ready to be placed             │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 7: PLACE - Open gripper                │
   │ Action: place() → Gripper OPENS             │
   │ Gripper: OPEN                               │
   │ NOTE: Object is released/dropped            │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 8: Lift up (gripper now empty)         │
   │ Position: (bin_x, bin_y, bin_z+20)          │
   │ Gripper: OPEN                               │
   └─────────────────────────────────────────────┘
   ↓
   ┌─────────────────────────────────────────────┐
   │ STEP 9: Return to HOME position             │
   │ Position: HOME_POSITION                     │
   │ Gripper: OPEN                               │
   └─────────────────────────────────────────────┘
   
END: Robot at HOME, ready for next item
```

---

## 🔧 Detailed Coordinate Reference

### Coordinate Values in Sequence:

#### **Pickup Area:**
```python
PICKUP_POSITION = (250, -135, 80, 0)  # Base pickup position

# Step 1: Above pickup (Gripper: OPEN)
move_to(pickup_x, pickup_y, pickup_z + 20, pickup_r)
# = (250, -135, 80 + 20, 0) = (250, -135, 100, 0)

# Step 2: At pickup level (Gripper: OPEN)
move_to(pickup_x, pickup_y, pickup_z + PICK_HEIGHT_OFFSET, pickup_r)
# = (250, -135, 80 + (-30), 0) = (250, -135, 50, 0)
# ↑ This is where gripper will CLOSE

# Step 3: Close gripper (Gripper: CLOSES) ⬛
pick()  # Gripper closes here!

# Step 4: Lift with object (Gripper: CLOSED) ⬛
move_to(pickup_x, pickup_y, pickup_z + 20, pickup_r)
# = (250, -135, 100, 0)
```

#### **Bin Area:**
```python
# Example: plastic bin at (250, 0, -30, 0)

# Step 5: Above bin (Gripper: CLOSED) ⬛
move_to(bin_x, bin_y, bin_z + 20, bin_r)
# = (250, 0, -30 + 20, 0) = (250, 0, -10, 0)

# Step 6: At bin level (Gripper: CLOSED) ⬛
move_to(bin_x, bin_y, bin_z + PLACE_HEIGHT_OFFSET, bin_r)
# = (250, 0, -30 + (-40), 0) = (250, 0, -70, 0)
# ↑ This is where gripper will OPEN

# Step 7: Open gripper (Gripper: OPENS) ⬜
place()  # Gripper opens here!

# Step 8: Lift up (Gripper: OPEN) ⬜
move_to(bin_x, bin_y, bin_z + 20, bin_r)
# = (250, 0, -10, 0)

# Step 9: Return home (Gripper: OPEN) ⬜
home()  # Moves to HOME_POSITION
```

---

## 📝 How to Calibrate Coordinates

### Step-by-Step Calibration Process:

1. **Test HOME Position:**
   ```python
   HOME_POSITION = (250, 0, 50, 0)  # Adjust this first
   ```
   - Should be a safe, clear position
   - Test with: `service.home()`

2. **Calibrate Pickup Position:**
   ```python
   PICKUP_POSITION = (250, -135, 80, 0)
   ```
   - Place an item at a known location
   - Manually move robot to that position
   - Read coordinates using `GetPose()` or manual positioning
   - Update `PICKUP_POSITION` with those values

3. **Adjust Pick Height:**
   ```python
   PICK_HEIGHT_OFFSET = -30  # Adjust this
   ```
   - If gripper doesn't reach object: Make more negative (e.g., -40)
   - If gripper goes too low: Make less negative (e.g., -20)
   - The final pickup Z = `pickup_z + PICK_HEIGHT_OFFSET`

4. **Calibrate Bin Positions:**
   ```python
   BIN_POSITIONS = {
       "plastic": (250, 0, -30, 0),  # Adjust each bin
       # ...
   }
   ```
   - For each bin, manually position robot above the center
   - Record the (x, y, z, r) coordinates
   - Update the corresponding bin position

5. **Adjust Place Height:**
   ```python
   PLACE_HEIGHT_OFFSET = -40  # Adjust this
   ```
   - Same logic as pick height
   - Final place Z = `bin_z + PLACE_HEIGHT_OFFSET`

---

## 🎯 Quick Reference: Gripper States

| Step | Position        | Gripper State | Action                  |
|------|-----------------|---------------|------------------------ |
| 1    | Above pickup    | OPEN          | Move to pickup area     |
| 2    | At pickup level | OPEN          | Descend to object       |
| 3    | At pickup level | **CLOSES**    | **Close gripper (PICK)**|
| 4    | Above pickup    | CLOSED        | Lift object             |
| 5    | Above bin       | CLOSED        | Move to bin             |
| 6    | At bin level    | CLOSED        | Descend to bin          |
| 7    | At bin level    | **OPENS**     | **Open gripper (PLACE)**|
| 8    | Above bin       | OPEN          | Lift up                 |
| 9    | Home            | OPEN          | Return home             |

---

## ⚠️ Important Notes

1. **Gripper is OPEN by default** - It only closes when `pick()` is called
2. **Gripper stays CLOSED** from Step 3 until Step 7
3. **Height offsets are relative** - They're added to the base Z position
4. **Coordinates are in millimeters** - Use precise measurements
5. **Test each position manually** before running automatic sorting

---

## 🔍 Code Locations Summary

**File:** `backend/services/dobot_service.py`

- **Line 31-38**: `BIN_POSITIONS` - Bin coordinates for each waste class
- **Line 81**: `PICKUP_POSITION` - Where items are placed
- **Line 86**: `HOME_POSITION` - Safe rest position
- **Line 91**: `PICK_HEIGHT_OFFSET` - How far down to pick
- **Line 92**: `PLACE_HEIGHT_OFFSET` - How far down to place

**Gripper Control:**
- **Line 311**: `pick()` - Closes gripper (on=1)
- **Line 357**: `place()` - Opens gripper (on=0)

---

## 💡 Tips for Calibration

1. **Start with small movements** - Test each coordinate incrementally
2. **Use manual control first** - Move robot manually to find correct positions
3. **Record coordinates** - Write down working coordinates as you find them
4. **Test height offsets separately** - Adjust PICK_HEIGHT_OFFSET and PLACE_HEIGHT_OFFSET independently
5. **Check gripper clearance** - Ensure gripper has enough space to open/close at each position

