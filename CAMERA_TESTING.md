# Camera Connection Testing Guide

## How to Test the DroidCam Connection

### Prerequisites

1. **Install DroidCam on your phone:**
   - Download DroidCam from Google Play Store or App Store
   - Install the DroidCam client on your phone

2. **Install DroidCam Server on your computer (optional):**
   - Download from: https://www.dev47apps.com/
   - This is only needed if you want to use USB connection
   - For WiFi connection, you only need the phone app

3. **Ensure phone and computer are on the same network:**
   - Both devices must be connected to the same WiFi network

### Testing Steps

#### Step 1: Start DroidCam on Phone

1. Open the DroidCam app on your phone
2. Select **WiFi IP** mode
3. Note the IP address displayed (e.g., `192.168.0.105`)
4. Tap **Start** to begin the server

#### Step 2: Connect from Web App

1. Start your Next.js development server:
   ```bash
   npm run dev
   ```

2. Open your browser and navigate to `http://localhost:3000`

3. Scroll down to the **Control Panel** section

4. Enter the DroidCam IP address in the input field:
   - Example: `192.168.0.105`
   - The IP should match what's shown in the DroidCam app

5. Click the **Connect Camera** button

#### Step 3: Verify Connection

**Success Indicators:**
- The Camera Feed card appears below the Control Panel
- You see a loading spinner briefly
- The live video feed from your phone camera displays
- The stream URL is shown below the video

**Error Indicators:**
- Red error message appears in the Control Panel (invalid IP)
- Camera Feed shows "Failed to connect to camera" with retry button
- Loading spinner continues indefinitely

### Troubleshooting

#### Issue: "Failed to connect to camera"

**Possible Causes:**
1. **Wrong IP address:**
   - Double-check the IP in the DroidCam app
   - Make sure there are no typos

2. **Phone and computer on different networks:**
   - Ensure both are on the same WiFi network
   - Check WiFi settings on both devices

3. **DroidCam not running:**
   - Verify DroidCam is started on your phone
   - Check that the server is active (green indicator)

4. **Firewall blocking connection:**
   - Check Windows Firewall settings
   - Allow connections on port 4747

5. **CORS/Network restrictions:**
   - Some networks block direct IP connections
   - Try using a different network or mobile hotspot

#### Issue: "Please enter a valid IP address"

- Make sure the IP format is correct: `xxx.xxx.xxx.xxx`
- No spaces before or after the IP
- Example format: `192.168.0.105`

#### Issue: Video feed is slow or laggy

- Check your WiFi connection strength
- Ensure phone and computer are close to the router
- Try reducing video quality in DroidCam settings

### Testing Checklist

- [ ] DroidCam app installed on phone
- [ ] Phone and computer on same WiFi network
- [ ] DroidCam server started on phone
- [ ] IP address noted from DroidCam app
- [ ] IP entered correctly in web app
- [ ] Connect button clicked
- [ ] Camera feed displays successfully
- [ ] Video stream is live and updating
- [ ] Disconnect button works correctly

### Expected Behavior

1. **On Connect:**
   - Input field becomes disabled
   - Button text changes to "Disconnect"
   - Camera Feed card appears below
   - Loading state shows briefly
   - Video stream loads and displays

2. **On Disconnect:**
   - Camera Feed card disappears
   - Input field becomes enabled
   - Button text changes back to "Connect"
   - Error state clears

3. **On Error:**
   - Error message displays in Control Panel (for validation errors)
   - Or error state shows in Camera Feed (for connection errors)
   - Retry button available in Camera Feed

### Network Configuration

**Default DroidCam Port:** `4747`

**Stream URL Format:** `http://<IP_ADDRESS>:4747/video`

**Example:** `http://192.168.0.105:4747/video`

### Notes

- The camera feed uses MJPEG streaming (Motion JPEG)
- The stream is displayed using an HTML `<img>` tag
- No backend server is required for basic streaming
- For production, you may want to add authentication or proxy through your backend

---

*Last Updated: [Current Date]*

