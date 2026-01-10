#!/usr/bin/env python3
"""
Camera check helper (supports USB and CSI cameras).

What it does:
- Opens camera via OpenCV (USB) or picamera2 (CSI) using config from config.yaml
- Prints detected properties (opened, width/height/fps)
- Captures a few frames and writes the last one to an image file (default: tmp_camera_test.jpg)

Usage:
  python scripts/check_camera.py
  python scripts/check_camera.py --type csi
  python scripts/check_camera.py --type usb --index 0 --out tmp.jpg
  python scripts/check_camera.py --type csi --frames 5
"""

import os
import sys
import argparse
import time


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def check_csi_camera(index, width, height, fps, frames, warmup, out_path):
    """Check CSI camera using picamera2"""
    try:
        from picamera2 import Picamera2
        import numpy as np
    except ImportError:
        print("[camera] ERROR: picamera2 not installed.")
        print("[camera] Install: sudo apt install -y python3-picamera2")
        raise SystemExit(2)
    
    print(f"[camera] CSI: trying index={index} {width}x{height} fps={fps}")
    
    try:
        picam2 = Picamera2(index)
        
        # Configure camera
        config = picam2.create_still_configuration(
            main={"size": (width, height), "format": "RGB888"},
            controls={"FrameRate": fps}
        )
        picam2.configure(config)
        picam2.start()
        
        print(f"[camera] CSI camera started successfully")
        time.sleep(max(0.0, warmup))
        
        last = None
        ok_frames = 0
        
        for i in range(max(1, frames)):
            try:
                frame = picam2.capture_array()
                if frame is not None:
                    ok_frames += 1
                    last = frame
                    print(f"[camera] frame {i+1}/{frames}: OK shape={frame.shape}")
                else:
                    print(f"[camera] frame {i+1}/{frames}: FAIL (None)")
            except Exception as e:
                print(f"[camera] frame {i+1}/{frames}: FAIL ({e})")
            time.sleep(0.05)
        
        picam2.stop()
        picam2.close()
        
        if last is None:
            print("[camera] ERROR: no frames captured.")
            raise SystemExit(3)
        
        # Convert RGB to BGR for OpenCV imwrite
        import cv2
        last_bgr = cv2.cvtColor(last, cv2.COLOR_RGB2BGR)
        
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        except Exception:
            pass
        
        if not cv2.imwrite(out_path, last_bgr):
            print(f"[camera] ERROR: failed to write {out_path}")
            raise SystemExit(4)
        
        print(f"[camera] saved: {out_path} (ok_frames={ok_frames})")
        
    except Exception as e:
        print(f"[camera] ERROR: CSI camera failed: {e}")
        print("[camera] Tips for CSI camera (OV5647):")
        print("  - Check camera ribbon cable is properly connected")
        print("  - Run: libcamera-hello --list-cameras")
        print("  - Run: sudo apt install -y python3-picamera2")
        print("  - Check camera is enabled in raspi-config")
        raise SystemExit(2)


def check_usb_camera(index, width, height, fps, frames, warmup, out_path):
    """Check USB camera using OpenCV"""
    import cv2
    
    print(f"[camera] USB: trying index={index} {width}x{height} fps={fps}")
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print("[camera] ERROR: cannot open USB camera.")
        # Extra diagnostics for Raspberry Pi
        try:
            import glob
            nodes = sorted(glob.glob("/dev/video*"))
            print(f"[camera] /dev/video* = {nodes}")
        except Exception:
            pass
        try:
            import glob
            for name_path in sorted(glob.glob("/sys/class/video4linux/video*/name")):
                vid = os.path.basename(os.path.dirname(name_path))
                with open(name_path, "r", encoding="utf-8", errors="ignore") as f:
                    print(f"[camera] {vid} name={f.read().strip()}")
        except Exception:
            pass
        try:
            import subprocess
            if subprocess.call(["bash", "-lc", "command -v v4l2-ctl >/dev/null"]) == 0:
                out = subprocess.check_output(["v4l2-ctl", "--list-devices"], text=True, stderr=subprocess.STDOUT)
                print("[camera] v4l2-ctl --list-devices:\n" + out.strip())
        except Exception:
            pass
        print("[camera] Tips:")
        print("  - check device exists: ls -la /dev/video*")
        print("  - list v4l2 devices: v4l2-ctl --list-devices  (sudo apt install v4l-utils)")
        print("  - check USB enumeration: lsusb  (you should see your USB camera vendor)")
        print("  - watch kernel logs while plugging camera: sudo dmesg -w | grep -i -E 'uvc|usb|video'")
        print("  - if using Pi CSI camera module: use --type csi instead")
        raise SystemExit(2)

    # Set requested properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    cap.set(cv2.CAP_PROP_FPS, float(fps))

    # Read actual properties
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    actual_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC) or 0)
    fourcc_str = "".join([chr((fourcc >> (8 * i)) & 0xFF) for i in range(4)])

    print(f"[camera] opened=yes actual={actual_w}x{actual_h} fps={actual_fps:.2f} fourcc={fourcc_str!r}")
    time.sleep(max(0.0, warmup))

    last = None
    ok_frames = 0
    for i in range(max(1, frames)):
        ok, frame = cap.read()
        if ok and frame is not None:
            ok_frames += 1
            last = frame
            print(f"[camera] frame {i+1}/{frames}: OK shape={frame.shape}")
        else:
            print(f"[camera] frame {i+1}/{frames}: FAIL")
        time.sleep(0.05)

    cap.release()

    if last is None:
        print("[camera] ERROR: no frames captured.")
        raise SystemExit(3)

    out_path_str = out_path
    try:
        os.makedirs(os.path.dirname(out_path_str), exist_ok=True)
    except Exception:
        pass

    if not cv2.imwrite(out_path_str, last):
        print(f"[camera] ERROR: failed to write {out_path_str}")
        raise SystemExit(4)

    print(f"[camera] saved: {out_path_str} (ok_frames={ok_frames})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="/home/pi/Projects/RobotEva/config.yaml")
    ap.add_argument("--type", choices=["usb", "csi"], default=None, help="Camera type (overrides config)")
    ap.add_argument("--index", type=int, default=None, help="Camera index (overrides config)")
    ap.add_argument("--width", type=int, default=None, help="Override width")
    ap.add_argument("--height", type=int, default=None, help="Override height")
    ap.add_argument("--fps", type=int, default=None, help="Override fps")
    ap.add_argument("--frames", type=int, default=3, help="How many frames to grab")
    ap.add_argument("--warmup", type=float, default=0.5, help="Warmup seconds before grabbing")
    ap.add_argument("--out", default="/home/pi/Projects/RobotEva/tmp_camera_test.jpg", help="Output jpg path")
    args = ap.parse_args()

    from robot_eva.core.config import Config

    cfg = Config(args.config)
    
    cam_type = args.type if args.type is not None else cfg.get("hardware.camera.type", "usb")
    index = args.index if args.index is not None else int(cfg.get("hardware.camera.index", 0))
    res = cfg.get("hardware.camera.resolution", [640, 480]) or [640, 480]
    fps = int(cfg.get("hardware.camera.fps", 30))

    width = args.width if args.width is not None else int(res[0])
    height = args.height if args.height is not None else int(res[1])
    fps = args.fps if args.fps is not None else fps

    if cam_type == "csi":
        check_csi_camera(index, width, height, fps, args.frames, args.warmup, args.out)
    else:
        check_usb_camera(index, width, height, fps, args.frames, args.warmup, args.out)


if __name__ == "__main__":
    main()


