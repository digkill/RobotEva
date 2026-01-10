#!/usr/bin/env python3
"""
Test script for OV5647 CSI camera with different modes.

OV5647 supported modes:
- 640x480 @ 58.92 fps
- 1296x972 @ 46.34 fps
- 1920x1080 @ 32.81 fps
- 2592x1944 @ 15.63 fps

Usage:
  python test_ov5647.py
  python test_ov5647.py --mode 0  # 640x480
  python test_ov5647.py --mode 1  # 1296x972 (default)
  python test_ov5647.py --mode 2  # 1920x1080
  python test_ov5647.py --mode 3  # 2592x1944
"""

import sys
import argparse
import time

try:
    from picamera2 import Picamera2
    import cv2
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install picamera2: sudo apt install -y python3-picamera2")
    print("Install OpenCV: pip3 install opencv-python")
    sys.exit(1)


CAMERA_MODES = [
    {"resolution": (640, 480), "fps": 58},
    {"resolution": (1296, 972), "fps": 46},
    {"resolution": (1920, 1080), "fps": 32},
    {"resolution": (2592, 1944), "fps": 15},
]


def test_camera(mode_index=1, frames=5, save_path="test_ov5647_capture.jpg", rotation=0):
    """Test OV5647 camera with specified mode"""
    
    if mode_index < 0 or mode_index >= len(CAMERA_MODES):
        print(f"Error: Invalid mode {mode_index}. Valid modes: 0-{len(CAMERA_MODES)-1}")
        return False
    
    mode = CAMERA_MODES[mode_index]
    resolution = mode["resolution"]
    fps = mode["fps"]
    
    print(f"\n{'='*60}")
    print(f"Testing OV5647 Camera")
    print(f"{'='*60}")
    print(f"Mode: {mode_index}")
    print(f"Resolution: {resolution[0]}x{resolution[1]}")
    print(f"FPS: {fps}")
    if rotation != 0:
        print(f"Rotation: {rotation}°")
    print(f"{'='*60}\n")
    
    try:
        # Initialize camera
        print("Initializing camera...")
        picam2 = Picamera2()
        
        # Get transform for rotation
        transform = None
        if rotation != 0:
            try:
                from libcamera import Transform
                transform = Transform()
                if rotation == 180:
                    transform.hflip = 1
                    transform.vflip = 1
                elif rotation == 90:
                    transform.vflip = 1
                elif rotation == 270:
                    transform.hflip = 1
            except ImportError:
                print("Warning: libcamera.Transform not available, rotation will not be applied")
        
        # Configure camera
        config_dict = {
            "main": {"size": resolution, "format": "RGB888"},
            "controls": {"FrameRate": fps}
        }
        if transform is not None:
            config_dict["transform"] = transform
            
        config = picam2.create_still_configuration(**config_dict)
        picam2.configure(config)
        
        print("Starting camera...")
        picam2.start()
        
        # Warmup
        print("Warming up (1 second)...")
        time.sleep(1.0)
        
        # Capture frames
        print(f"\nCapturing {frames} frames...")
        captured_frames = []
        capture_times = []
        
        for i in range(frames):
            start = time.time()
            frame = picam2.capture_array()
            elapsed = time.time() - start
            
            if frame is not None:
                captured_frames.append(frame)
                capture_times.append(elapsed)
                print(f"  Frame {i+1}/{frames}: OK - shape={frame.shape}, capture time={elapsed*1000:.1f}ms")
            else:
                print(f"  Frame {i+1}/{frames}: FAILED")
            
            time.sleep(0.05)
        
        # Statistics
        if capture_times:
            avg_time = sum(capture_times) / len(capture_times)
            avg_fps = 1.0 / avg_time if avg_time > 0 else 0
            print(f"\nCapture statistics:")
            print(f"  Average capture time: {avg_time*1000:.1f}ms")
            print(f"  Average FPS: {avg_fps:.1f}")
        
        # Save last frame
        if captured_frames:
            last_frame = captured_frames[-1]
            # Convert RGB to BGR for OpenCV
            last_frame_bgr = cv2.cvtColor(last_frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(save_path, last_frame_bgr)
            print(f"\nSaved last frame to: {save_path}")
            print(f"Frame info: {last_frame.shape[1]}x{last_frame.shape[0]}, {last_frame.shape[2]} channels")
        
        # Cleanup
        print("\nStopping camera...")
        picam2.stop()
        picam2.close()
        
        print(f"\n{'='*60}")
        print("Test completed successfully!")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"\nError during camera test: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Check camera ribbon cable connection")
        print("  2. Run: libcamera-hello --list-cameras")
        print("  3. Run: sudo raspi-config -> Interface Options -> Camera (enable)")
        print("  4. Reboot if you just enabled the camera")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test OV5647 CSI camera")
    parser.add_argument("--mode", type=int, default=1, 
                       help="Camera mode (0=640x480, 1=1296x972, 2=1920x1080, 3=2592x1944)")
    parser.add_argument("--frames", type=int, default=5,
                       help="Number of frames to capture")
    parser.add_argument("--output", type=str, default="test_ov5647_capture.jpg",
                       help="Output file path for captured image")
    parser.add_argument("--rotation", type=int, default=0, choices=[0, 90, 180, 270],
                       help="Rotate image (0, 90, 180, or 270 degrees)")
    parser.add_argument("--list", action="store_true",
                       help="List available camera modes")
    
    args = parser.parse_args()
    
    if args.list:
        print("\nOV5647 Camera Modes:")
        print("="*60)
        for i, mode in enumerate(CAMERA_MODES):
            res = mode["resolution"]
            fps = mode["fps"]
            print(f"Mode {i}: {res[0]}x{res[1]} @ {fps} fps")
        print("="*60 + "\n")
        return
    
    success = test_camera(args.mode, args.frames, args.output, args.rotation)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
