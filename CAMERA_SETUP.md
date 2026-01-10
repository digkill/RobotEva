# OV5647 CSI Camera Setup for RobotEva

This guide explains how to use the OV5647 CSI camera module with RobotEva.

## Camera Specifications

The OV5647 is a 5MP CSI camera that supports the following modes:

| Mode | Resolution | Max FPS | Use Case |
|------|-----------|---------|----------|
| 0 | 640x480 | 58.92 | Fast motion tracking, low latency |
| 1 | 1296x972 | 46.34 | **Recommended** - Balance of quality and speed |
| 2 | 1920x1080 | 32.81 | High quality video, Full HD |
| 3 | 2592x1944 | 15.63 | Maximum resolution, still photos |

## Hardware Setup

1. **Connect the camera ribbon cable:**
   - Power off your Raspberry Pi
   - Locate the CSI camera connector (between HDMI and audio jack)
   - Lift the black plastic clip gently
   - Insert the ribbon cable with blue side facing the audio jack
   - Push the clip back down to secure

2. **Enable camera interface:**
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Yes
   # Reboot when prompted
   ```

3. **Verify camera detection:**
   ```bash
   libcamera-hello --list-cameras
   ```
   You should see output showing the OV5647 camera.

## Software Requirements

The OV5647 camera requires `picamera2` library (pre-installed on Raspberry Pi OS Bookworm):

```bash
# Install picamera2 if not present
sudo apt install -y python3-picamera2

# Install OpenCV if needed
pip3 install opencv-python
```

## Configuration

The camera is configured in `config.yaml`:

```yaml
hardware:
  camera:
    type: csi              # "csi" for OV5647, "usb" for webcam
    index: 0               # Camera index (usually 0)
    resolution: [1296, 972]  # Resolution (Mode 1 - recommended)
    fps: 46                # Frame rate
```

### Recommended Settings

**For face tracking (default):**
```yaml
resolution: [1296, 972]
fps: 46
```

**For fast motion tracking:**
```yaml
resolution: [640, 480]
fps: 58
```

**For high-quality vision/AI:**
```yaml
resolution: [1920, 1080]
fps: 32
```

**For still photography:**
```yaml
resolution: [2592, 1944]
fps: 15
```

## Testing the Camera

### 1. Quick Test with libcamera

```bash
# Take a test photo
libcamera-still -o test.jpg

# Show 5-second preview
libcamera-hello --timeout 5000
```

### 2. Test with RobotEva Scripts

**Test OV5647 with different modes:**
```bash
# Test default mode (1296x972 @ 46fps)
python3 test_ov5647.py

# List all available modes
python3 test_ov5647.py --list

# Test specific mode
python3 test_ov5647.py --mode 0  # 640x480
python3 test_ov5647.py --mode 1  # 1296x972
python3 test_ov5647.py --mode 2  # 1920x1080
python3 test_ov5647.py --mode 3  # 2592x1944

# Capture more frames
python3 test_ov5647.py --mode 1 --frames 10
```

**Test using check_camera script:**
```bash
# Test CSI camera with config.yaml settings
python3 scripts/check_camera.py --type csi

# Test with custom resolution
python3 scripts/check_camera.py --type csi --width 1920 --height 1080 --fps 32

# Capture and save test image
python3 scripts/check_camera.py --type csi --out my_test.jpg
```

### 3. Test Camera in RobotEva

The camera will be automatically initialized when RobotEva starts. Check the logs:

```bash
# Run RobotEva
python3 main.py

# You should see in logs:
# [INFO] CSI камера инициализирована (разрешение: [1296, 972], FPS: 46)
```

## Camera Usage in Code

The camera is managed by `CameraManager` class in `robot_eva/hardware/camera.py`:

```python
# Camera is available as robot.camera
frame = await robot.camera.capture_frame()

# Save a photo
await robot.camera.save_frame("photo.jpg")

# Check if camera is available
if robot.camera.is_available():
    print("Camera ready!")
```

## Troubleshooting

### Camera not detected

```bash
# Check camera detection
libcamera-hello --list-cameras

# Check for errors
dmesg | grep -i camera

# Verify camera interface is enabled
vcgencmd get_camera
# Should show: supported=1 detected=1
```

### picamera2 import error

```bash
# Install picamera2
sudo apt update
sudo apt install -y python3-picamera2

# Verify installation
python3 -c "from picamera2 import Picamera2; print('OK')"
```

### Poor image quality

1. **Check focus:** OV5647 camera has a fixed focus. Make sure objects are ~30cm+ away
2. **Check lighting:** CSI cameras perform poorly in low light
3. **Clean the lens:** Gently clean the camera lens with a soft cloth
4. **Adjust exposure:** You can add camera controls in the code:
   ```python
   controls={"FrameRate": fps, "ExposureTime": 10000, "AnalogueGain": 1.0}
   ```

### Ribbon cable issues

- Ensure cable is fully inserted with contacts facing the right way
- Check for damage or tears in the ribbon cable
- Try a different ribbon cable if available
- Make sure the connector clip is firmly pressed down

### Performance issues

- Use lower resolution mode for faster frame rates
- Ensure Raspberry Pi is not throttling (check temperature)
- Close unnecessary applications to free up RAM
- Consider using a cooling fan for the Pi

## Switching Back to USB Camera

If you want to use a USB webcam instead:

1. Edit `config.yaml`:
   ```yaml
   hardware:
     camera:
       type: usb
       index: 0
       resolution: [640, 480]
       fps: 30
   ```

2. Test USB camera:
   ```bash
   python3 scripts/check_camera.py --type usb
   ```

## Advanced Configuration

### Multiple Cameras

If you have both CSI and USB cameras connected:

```yaml
# config.yaml - Use CSI camera (index 0)
camera:
  type: csi
  index: 0

# To use USB camera instead
# camera:
#   type: usb
#   index: 0  # or 1, 2, etc.
```

### Custom Camera Controls

You can modify `robot_eva/hardware/camera.py` to add camera controls:

```python
config = picam2.create_still_configuration(
    main={"size": tuple(self.resolution), "format": "RGB888"},
    controls={
        "FrameRate": self.fps,
        "ExposureTime": 10000,  # microseconds
        "AnalogueGain": 1.5,    # gain multiplier
        "Brightness": 0.0,      # -1.0 to 1.0
        "Contrast": 1.0,        # contrast multiplier
    }
)
```

## References

- [Picamera2 Documentation](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [OV5647 Datasheet](https://www.raspberrypi.com/documentation/accessories/camera.html)
- [Raspberry Pi Camera Guide](https://www.raspberrypi.com/documentation/computers/camera_software.html)

## Summary

✅ OV5647 CSI camera is now configured and ready to use  
✅ Recommended mode: 1296x972 @ 46fps for best balance  
✅ Test with: `python3 test_ov5647.py`  
✅ Face tracking and vision features will use the CSI camera automatically
