# RobotEva v1.1.2 - Face Tracking & Interactive Features

**Release Date:** January 10, 2026  
**Commit:** 23b9e33  
**Tag:** v1.1.2

## 🎉 Major Features

### ✅ Face Tracking (Отслеживание лица)
- **Fixed:** `module 'cv2' has no attribute 'data'` error
- **Added:** Local Haar Cascade file (909K) for opencv-python-headless compatibility
- **Optimized:** Smooth head movements without jerking
- **Performance:** 5 FPS, optimized for smooth tracking
- **Local Processing:** 100% offline using OpenCV Haar Cascade

**Configuration:**
```yaml
fps: 5                    # Smooth updates every 200ms
deadzone: 0.20            # Ignore movements < 20%
smoothing_alpha: 0.90     # Strong smoothing (90% old + 10% new)
smooth_steps: 15          # More interpolation steps
smooth_delay: 0.025       # Slower, smoother movement
```

### ✅ Touch Animations (Тач-анимации)
- **Added:** 10 funny face animations triggered by touchscreen tap
- **Animations:** dizzy, stars, hearts, silly, crazy, sparkle, laugh, blush, surprise_big, money
- **Behavior:** Random selection, automatic revert to previous animation
- **Integration:** Touch event handling in display_small_sdl.py

### ✅ Activity Control (Контроль активности)
- **Stop Command:** "стоп", "замолчи", "молчать" → Robot goes silent
- **Resume Command:** "давай поговорим", "поговорим" → Robot resumes conversation
- **Feature:** Controls idle_chat behavior and command processing
- **Response:** Custom TTS responses for stop/resume

### ✅ Improved Gesture Recognition (Улучшенные жесты)
- **Speed:** Recognition time reduced from 30+ seconds to 1.5-3 seconds
- **Accuracy:** More sensitive OpenAI Vision prompts
- **New Gesture:** "cute" (peace sign ✌️, waving 👋, thumbs up 👍)
- **Optimization:** Active window (30 seconds) to reduce API costs

**Parameters:**
```yaml
interval_seconds: 1.5         # Was 15.0 (10x faster!)
consecutive_hits: 1           # Was 2 (instant recognition!)
debounce_seconds: 8.0         # Prevent rapid re-triggering
```

### ✅ OV5647 CSI Camera Support
- **Integration:** Full support for OV5647 CSI camera
- **Resolution:** 1296x972 @ 46 FPS
- **Rotation:** Configurable image rotation (0°, 90°, 180°, 270°)
- **Configuration:** libcamera.Transform support for CSI cameras

## 🔧 Technical Improvements

### Face Tracking Optimization
- **Before:** Jerky movements, updates every 125ms
- **After:** Smooth movements, updates every 200ms
- **Algorithm:** Low-pass filter with smoothing_alpha=0.90
- **Deadzone:** 0.20 (ignores small movements < 20%)
- **Interpolation:** 15 steps × 25ms = 375ms smooth movement

### Gesture Recognition Enhancement
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Response Time | 30+ sec | 1.5-3 sec | **10x faster** |
| Consecutive Hits | 2 | 1 | **Instant** |
| API Calls | Continuous | 30s window | **Cost optimized** |

### Camera Integration
- **CSI Support:** picamera2 integration for OV5647
- **USB Fallback:** Backward compatibility with USB cameras
- **Rotation:** Dynamic rotation via config.yaml
- **Error Handling:** Safe fallback to local Haar Cascade files

## 📂 Files Changed

### Modified (12 files)
- `robot_eva/behaviors/face_tracking.py` - Fixed cv2.data error, added fallback
- `robot_eva/behaviors/heart_gesture.py` - Enhanced prompts
- `robot_eva/behaviors/gun_gesture.py` - Enhanced prompts
- `robot_eva/core/robot.py` - Activity control, cute gesture integration
- `robot_eva/emotions/animations.py` - 10 new touch animations
- `robot_eva/hardware/camera.py` - OV5647 support, rotation
- `robot_eva/hardware/display.py` - Touch animation management
- `robot_eva/hardware/display_small_sdl.py` - Touch event capture
- `config.yaml` - Face tracking, gestures, activity, touch settings
- `requirements.txt` - Updated for Python 3.13
- `README.md` - Documentation updates
- `scripts/check_camera.py` - CSI camera testing

### Created (28 files)
- `robot_eva/behaviors/cute_gesture.py` - New gesture behavior
- `data/haarcascade_frontalface_default.xml` - Haar Cascade (909K)
- `test_face_tracking.py` - Face tracking test script
- `test_touch_animations.py` - Touch animations test
- `test_ov5647.py` - Camera test script
- `test_camera_from_config.py` - Config-based camera test
- `check_camera_deps.sh` - Dependency checker
- `install_camera_deps.sh` - Dependency installer
- `КАМЕРА_OV5647.md` - Camera guide (Russian)
- **20+ documentation files** (MD & TXT formats, English & Russian)

## 📚 Documentation

### Face Tracking
- `FACE_TRACKING_INFO.md` - Complete documentation (EN)
- `FACE_TRACKING_SUMMARY.txt` - Quick reference (RU)
- `FACE_TRACKING_QUICKSTART.txt` - Quick start guide
- `FACE_TRACKING_FIX_COMPLETED.txt` - Bug fixes
- `FACE_TRACKING_SMOOTH.txt` - Smoothness optimization

### Touch Animations
- `TOUCH_ANIMATIONS.md` - Complete documentation
- `TOUCH_ANIMATIONS_SUMMARY.txt` - Quick reference (RU)
- `TOUCH_ANIMATIONS_QUICKSTART.txt` - Quick start

### Gestures
- `GESTURE_RECOGNITION_IMPROVEMENTS.md` - Improvements guide
- `GESTURE_IMPROVEMENTS_SUMMARY.txt` - Quick reference (RU)

### Activity Control
- `ACTIVITY_CONTROL.md` - Feature documentation
- `ACTIVITY_CONTROL_SUMMARY.txt` - Quick reference (RU)

### Camera
- `КАМЕРА_OV5647.md` - Complete setup guide (RU)
- `CAMERA_SETUP.md` - Setup guide (EN)
- `OV5647_INTEGRATION.md` - Technical details

## 🖥️ Platform

### Hardware
- Raspberry Pi 5
- OV5647 CSI Camera (1296x972, 46 FPS)
- Touchscreen displays (SDL/FBDEV)

### Software
- Raspberry Pi OS (64-bit)
- Python 3.13.5
- OpenCV 4.10.0 (headless)
- libcamera v0.6.0
- picamera2

## 📊 Statistics

- **Files Changed:** 40
- **Lines Added:** +6,400
- **Lines Removed:** -178
- **Documentation:** 20+ files
- **New Features:** 5 major
- **Bug Fixes:** 3 critical

## 🐛 Bug Fixes

1. **Face Tracking Error:** Fixed `module 'cv2' has no attribute 'data'`
   - Root cause: opencv-python-headless doesn't include cv2.data
   - Solution: Downloaded Haar Cascade file locally, added fallback logic

2. **Jerky Head Movements:** Optimized face tracking parameters
   - Reduced FPS from 8 to 5
   - Increased deadzone from 0.07 to 0.20
   - Enhanced smoothing from 0.75 to 0.90

3. **Slow Gesture Recognition:** Reduced response time by 10x
   - Changed interval from 15s to 1.5s
   - Reduced consecutive_hits from 2 to 1
   - Enhanced Vision API prompts

## 🚀 Usage

### Install
```bash
git clone <repository>
cd RobotEva
git checkout v1.1.2
pip install -r requirements.txt
```

### Run
```bash
python3 main.py
```

### Test Face Tracking
```bash
python3 test_face_tracking.py
```

### Test Touch Animations
```bash
python3 test_touch_animations.py
```

## 📝 Configuration Examples

### Enable Face Tracking
```yaml
behavior:
  face_tracking:
    enabled: true
    fps: 5
    deadzone: 0.20
    smoothing_alpha: 0.90
```

### Enable Touch Animations
```yaml
hardware:
  display:
    small:
      touch:
        enabled: true
        animations:
          - dizzy
          - stars
          - hearts
```

### Configure Gestures
```yaml
behavior:
  gestures:
    enabled: true
    active_window_seconds: 30
    heart:
      interval_seconds: 1.5
      consecutive_hits: 1
```

## 🔜 Future Improvements

- [ ] Multi-face tracking
- [ ] Face recognition with memory
- [ ] Custom touch animation editor
- [ ] More gesture types
- [ ] Performance profiling dashboard

## 🙏 Credits

- **Developer:** AI Assistant (Claude Sonnet 4.5)
- **Project:** RobotEva
- **Platform:** Raspberry Pi 5
- **Date:** January 10, 2026

## 📄 License

[Your License Here]

---

**Full Changelog:** v1.1.1...v1.1.2
