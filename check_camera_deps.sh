#!/bin/bash
# Check OV5647 Camera Dependencies and Configuration

echo "========================================"
echo "OV5647 Camera Dependency Check"
echo "========================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: Not running on Raspberry Pi"
else
    echo "✓ Running on: $(cat /proc/device-tree/model)"
fi
echo ""

# Check picamera2
echo "Checking picamera2..."
if python3 -c "from picamera2 import Picamera2" 2>/dev/null; then
    echo "✓ picamera2 is installed"
else
    echo "✗ picamera2 is NOT installed"
    echo "  Install with: sudo apt install -y python3-picamera2"
fi
echo ""

# Check OpenCV
echo "Checking OpenCV..."
if python3 -c "import cv2" 2>/dev/null; then
    CV_VERSION=$(python3 -c "import cv2; print(cv2.__version__)" 2>/dev/null)
    echo "✓ OpenCV is installed (version: $CV_VERSION)"
else
    echo "✗ OpenCV is NOT installed"
    echo "  Install with: pip3 install opencv-python"
fi
echo ""

# Check numpy
echo "Checking numpy..."
if python3 -c "import numpy" 2>/dev/null; then
    NP_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null)
    echo "✓ numpy is installed (version: $NP_VERSION)"
else
    echo "✗ numpy is NOT installed"
    echo "  Install with: pip3 install numpy"
fi
echo ""

# Check libcamera
echo "Checking libcamera..."
if command -v libcamera-hello >/dev/null 2>&1; then
    echo "✓ libcamera tools are installed"
else
    echo "✗ libcamera tools are NOT installed"
    echo "  Install with: sudo apt install -y libcamera-apps"
fi
echo ""

# Check camera interface
echo "Checking camera interface..."
if command -v vcgencmd >/dev/null 2>&1; then
    CAM_STATUS=$(vcgencmd get_camera 2>/dev/null)
    if echo "$CAM_STATUS" | grep -q "detected=1"; then
        echo "✓ Camera interface is enabled and camera detected"
        echo "  Status: $CAM_STATUS"
    elif echo "$CAM_STATUS" | grep -q "supported=1"; then
        echo "⚠️  Camera interface is enabled but no camera detected"
        echo "  Status: $CAM_STATUS"
        echo "  Check camera ribbon cable connection"
    else
        echo "✗ Camera interface may not be enabled"
        echo "  Status: $CAM_STATUS"
        echo "  Enable with: sudo raspi-config -> Interface Options -> Camera"
    fi
else
    echo "⚠️  vcgencmd not available (not on Raspberry Pi?)"
fi
echo ""

# List cameras with libcamera
echo "Listing cameras with libcamera..."
if command -v libcamera-hello >/dev/null 2>&1; then
    CAMERAS=$(libcamera-hello --list-cameras 2>&1)
    if echo "$CAMERAS" | grep -q "ov5647"; then
        echo "✓ OV5647 camera detected!"
        echo "$CAMERAS" | grep -A3 "ov5647"
    elif echo "$CAMERAS" | grep -q "Available cameras"; then
        echo "⚠️  Camera detected but not OV5647:"
        echo "$CAMERAS" | head -20
    else
        echo "✗ No cameras detected"
        echo "  Output: $CAMERAS"
    fi
else
    echo "⚠️  libcamera-hello not available"
fi
echo ""

# Check config.yaml
echo "Checking config.yaml..."
if [ -f "/home/pi/Projects/RobotEva/config.yaml" ]; then
    echo "✓ config.yaml exists"
    CAM_TYPE=$(grep -A5 "^  camera:" /home/pi/Projects/RobotEva/config.yaml | grep "type:" | awk '{print $2}')
    CAM_RES=$(grep -A5 "^  camera:" /home/pi/Projects/RobotEva/config.yaml | grep "resolution:" | awk '{print $2}')
    CAM_FPS=$(grep -A5 "^  camera:" /home/pi/Projects/RobotEva/config.yaml | grep "fps:" | awk '{print $2}')
    
    echo "  Camera type: $CAM_TYPE"
    echo "  Resolution: $CAM_RES"
    echo "  FPS: $CAM_FPS"
    
    if [ "$CAM_TYPE" = "csi" ]; then
        echo "  ✓ Configured for CSI camera (OV5647)"
    else
        echo "  ⚠️  Configured for $CAM_TYPE camera"
        echo "     Change 'type: csi' in config.yaml to use OV5647"
    fi
else
    echo "✗ config.yaml not found"
fi
echo ""

# Summary
echo "========================================"
echo "Summary"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. If any dependencies are missing, install them"
echo "2. If camera is not detected, check ribbon cable"
echo "3. Test camera with: python3 test_ov5647.py"
echo "4. Run RobotEva with: python3 main.py"
echo ""
