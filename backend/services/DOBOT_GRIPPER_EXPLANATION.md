# Dobot Gripper Explanation

## How the Gripper Works

The Dobot Magician uses a **mechanical gripper end effector**. Here's how it works:

### Components:
- **Gripper**: Mechanical two-finger gripper at the end of the robot arm
- **Actuator**: Servo motor that opens/closes the gripper
- **Control**: SDK controls the gripper open/close state

### Operation:

1. **PICK (pick() function)**:
   - Robot moves to position where object can be grasped
   - Robot descends to object
   - `SetEndEffectorGripper(api, 1, 1)` is called
     - `enableCtrl=1`: Enable control of the gripper
     - `on=1`: **CLOSE** the gripper (fingers come together)
   - Gripper fingers close around the object
   - Object is gripped between the fingers
   - Robot can now lift and move the object

2. **PLACE (place() function)**:
   - Robot moves to bin position above drop point
   - Robot descends to drop height
   - `SetEndEffectorGripper(api, 1, 0)` is called
     - `enableCtrl=1`: Keep control enabled
     - `on=0`: **OPEN** the gripper (fingers spread apart)
   - Gripper fingers open, releasing the object
   - Object drops into the bin
   - Robot lifts up and returns home

### Important Notes:

- **Position Matters**: The gripper must be positioned so it can grasp the object properly
- **Object Size**: Gripper can handle various sizes (check gripper opening width)
- **Grip Strength**: Gripper applies pressure to hold objects - ensure objects aren't too fragile
- **Orientation**: May need to adjust approach angle depending on object shape

### Code Implementation:

```python
# Close gripper (PICK)
dType.SetEndEffectorGripper(api, enableCtrl=1, on=1, isQueued=1)
# ↑ This CLOSES the gripper (grips object)

# Open gripper (PLACE)  
dType.SetEndEffectorGripper(api, enableCtrl=1, on=0, isQueued=1)
# ↑ This OPENS the gripper (releases object)
```

---

## Safe Coordinates Restored

I've restored safe default coordinates that should work for most setups:

### Bin Positions (mm):
- **paper**: (200, 100, -30, 0)
- **plastic**: (250, 0, -30, 0)
- **glass**: (200, -100, -30, 0)
- **biological**: (150, 100, -30, 0)
- **trash**: (150, 0, -30, 0)

### Other Positions:
- **PICKUP_POSITION**: (200, 0, -20, 0) - Where items are placed for sorting
- **HOME_POSITION**: (250, 0, 50, 0) - Safe starting/resting position

### Important:
- These are **safe defaults** but you MUST calibrate them for your specific setup
- Z coordinates (height) may need adjustment based on your table/surface height
- Test each position manually before running automatic sorting

---

## Enhanced Error Logging

I've added detailed logging to help debug issues:

- Connection attempts are now logged
- Each step of the sorting sequence is printed
- Errors include full tracebacks
- Success/failure messages are clear

### Check Backend Console:
When you make a prediction, watch the backend console output. You should see:
```
Attempting to connect to Dobot...
Dobot connected successfully on port COM5

==================================================
Starting sorting sequence for: plastic
==================================================
ML Prediction: plastic
Mapped to bin: plastic
Target bin position: (250, 0, -30, 0)

Step 1/9: Moving above pickup position...
Step 2/9: Descending to pickup position...
...
```

If the robot doesn't move, check the console for error messages!

---

## Troubleshooting

### Robot doesn't move at all?
1. Check backend console for errors
2. Verify USB connection to Dobot
3. Check if COM port is correct (try specifying manually)
4. Ensure Dobot is powered on
5. Check if DLL files are in `backend/dobot_magician/`

### Robot moves but doesn't pick?
1. Check gripper connection and wiring
2. Verify object is within reach and graspable
3. Check if object size fits within gripper opening
4. Verify Z coordinates (height) are correct for grasping
5. Ensure gripper can properly close around the object

### Connection fails?
1. Try specifying port manually: `service.connect(port="COM5")`
2. Check Windows Device Manager for COM port number
3. Ensure no other software is using the Dobot
4. Try unplugging and reconnecting USB cable

