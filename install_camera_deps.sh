#!/bin/bash
# Install OV5647 Camera Dependencies for RobotEva

set -e  # Exit on error

echo "========================================"
echo "Installing OV5647 Camera Dependencies"
echo "========================================"
echo ""

# Check if running as pi user or with sudo access
if [ "$EUID" -eq 0 ]; then 
    echo "Note: Running as root"
    SUDO=""
else
    SUDO="sudo"
fi

# Update package list
echo "Updating package list..."
$SUDO apt-get update
echo ""

# Install system packages
echo "Installing system packages..."
$SUDO apt-get install -y \
    python3-picamera2 \
    libcamera-apps \
    libcamera-tools \
    python3-opencv \
    python3-numpy
echo ""

# Install Python packages from requirements.txt
echo "Installing Python packages from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --break-system-packages 2>/dev/null || \
    pip3 install -r requirements.txt
    echo "✓ Python packages installed"
else
    echo "⚠️  requirements.txt not found, installing OpenCV manually..."
    pip3 install opencv-python numpy --break-system-packages 2>/dev/null || \
    pip3 install opencv-python numpy
fi
echo ""

# Verify installations
echo "Verifying installations..."
echo ""

# Check picamera2
echo -n "picamera2: "
if python3 -c "from picamera2 import Picamera2" 2>/dev/null; then
    echo "✓ OK"
else
    echo "✗ FAILED"
fi

# Check OpenCV
echo -n "OpenCV: "
if python3 -c "import cv2" 2>/dev/null; then
    CV_VERSION=$(python3 -c "import cv2; print(cv2.__version__)" 2>/dev/null)
    echo "✓ OK (version: $CV_VERSION)"
else
    echo "✗ FAILED"
fi

# Check numpy
echo -n "numpy: "
if python3 -c "import numpy" 2>/dev/null; then
    NP_VERSION=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null)
    echo "✓ OK (version: $NP_VERSION)"
else
    echo "✗ FAILED"
fi

# Check libcamera
echo -n "libcamera-hello: "
if command -v libcamera-hello >/dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED"
fi

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Connect your OV5647 camera to the CSI port"
echo "2. Enable camera interface:"
echo "   sudo raspi-config"
echo "   -> Interface Options -> Camera -> Yes"
echo "   -> Reboot"
echo ""
echo "3. After reboot, verify camera detection:"
echo "   libcamera-hello --list-cameras"
echo ""
echo "4. Test camera with RobotEva:"
echo "   python3 test_ov5647.py"
echo ""
echo "5. Run dependency check:"
echo "   bash check_camera_deps.sh"
echo ""
