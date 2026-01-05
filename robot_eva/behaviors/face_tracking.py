import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import cv2
import numpy as np


@dataclass
class FaceTrackingState:
    last_seen_ts: float = 0.0
    yaw_target: float = 0.0
    pitch_target: float = 0.0


class FaceTrackingBehavior:
    """
    Simple face tracking:
    - detect face in camera frames (OpenCV Haar cascade)
    - convert face offset from center into head yaw/pitch angles
    - move servos smoothly within configured limits

    Designed to be safe:
    - respects behavior.motion.center/range (or explicit face_tracking max degrees)
    - low-pass smoothing to reduce jitter
    - can pause while speaking if configured
    """

    def __init__(self, config: Any, camera_manager: Any, servo_controller: Any):
        self.config = config
        self.camera = camera_manager
        self.servos = servo_controller
        self.logger = logging.getLogger(__name__)

        self.enabled: bool = bool(config.get("behavior.face_tracking.enabled", False))
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._paused: bool = False

        self._cascade: Optional[cv2.CascadeClassifier] = None
        self._state = FaceTrackingState()

    async def initialize(self) -> None:
        if not self.enabled:
            return
        if not self.camera or not self.servos:
            self.logger.info("FaceTracking: camera/servos not available, disabled.")
            self.enabled = False
            return

        # Haar cascade path
        cascade_path = str(
            self.config.get(
                "behavior.face_tracking.cascade_path",
                str(getattr(cv2.data, "haarcascades", "")) + "haarcascade_frontalface_default.xml",
            )
        )
        try:
            self._cascade = cv2.CascadeClassifier(cascade_path)
            if self._cascade.empty():
                raise RuntimeError(f"cascade empty: {cascade_path}")
        except Exception as e:
            self.logger.warning(f"FaceTracking: failed to load cascade ({cascade_path}): {e}")
            self.enabled = False
            self._cascade = None
            return

        self.logger.info("FaceTracking enabled")

    async def start(self) -> None:
        if not self.enabled:
            return
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="face-tracking")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._task = None

    def set_paused(self, paused: bool) -> None:
        # Soft pause flag; loop checks config + this flag.
        self._paused = bool(paused)

    def _get_centers_and_limits(self) -> Tuple[float, float, float, float]:
        # Centers (дефолт 0° для всех серв)
        yaw_center = float(self.config.get("behavior.motion.center.head_yaw", 0))
        pitch_center = float(self.config.get("behavior.motion.center.neck_pitch", 0))

        # Max offsets (degrees). Prefer explicit face_tracking config, else use motion ranges.
        yaw_max = float(
            self.config.get(
                "behavior.face_tracking.max_yaw_deg",
                self.config.get("behavior.motion.range.head_yaw", 25),
            )
        )
        pitch_max = float(
            self.config.get(
                "behavior.face_tracking.max_pitch_deg",
                self.config.get("behavior.motion.range.head_pitch", 15),
            )
        )
        yaw_max = max(1.0, min(60.0, yaw_max))
        pitch_max = max(1.0, min(45.0, pitch_max))
        return yaw_center, pitch_center, yaw_max, pitch_max

    async def _move_head(self, yaw: float, pitch: float) -> None:
        yaw_id = getattr(self.servos, "SERVO_HEAD_YAW", 2)    # Канал 2
        pitch_id = getattr(self.servos, "SERVO_HEAD_PITCH", 0)  # Канал 0

        # Small smoothing move; for MQTT this becomes a short sequence of moves.
        steps = int(self.config.get("behavior.face_tracking.smooth_steps", 3))
        delay = float(self.config.get("behavior.face_tracking.smooth_delay", 0.02))
        steps = max(1, min(8, steps))
        delay = max(0.0, min(0.08, delay))

        try:
            if hasattr(self.servos, "move_smooth"):
                await self.servos.move_smooth(yaw_id, yaw, steps=steps, delay=delay)
                await self.servos.move_smooth(pitch_id, pitch, steps=steps, delay=delay)
            else:
                await self.servos.move(yaw_id, yaw)
                await self.servos.move(pitch_id, pitch)
        except Exception:
            # Keep loop resilient
            pass

    async def _loop(self) -> None:
        if not self._cascade:
            return

        fps = float(self.config.get("behavior.face_tracking.fps", 8.0))
        fps = max(2.0, min(20.0, fps))
        interval = 1.0 / fps

        alpha = float(self.config.get("behavior.face_tracking.smoothing_alpha", 0.75))
        alpha = max(0.0, min(0.95, alpha))

        deadzone = float(self.config.get("behavior.face_tracking.deadzone", 0.07))
        deadzone = max(0.0, min(0.3, deadzone))

        invert_yaw = bool(self.config.get("behavior.face_tracking.invert_yaw", False))
        invert_pitch = bool(self.config.get("behavior.face_tracking.invert_pitch", True))

        # Placeholder for future: gate by presence sensor if wired into this behavior.
        # (RobotEva has SensorManager, but we keep this behavior decoupled.)
        require_presence = bool(self.config.get("behavior.face_tracking.require_human_detected", False))
        return_to_center_s = float(self.config.get("behavior.face_tracking.return_to_center_seconds", 2.0))
        return_to_center_s = max(0.0, min(30.0, return_to_center_s))

        debug = bool(self.config.get("behavior.face_tracking.debug", False))
        log_on_face = bool(self.config.get("behavior.face_tracking.log_on_face_detected", True))
        log_every_s = float(self.config.get("behavior.face_tracking.debug_log_interval_seconds", 2.0))
        log_every_s = max(0.5, min(10.0, log_every_s))
        last_log_ts = 0.0
        had_face = False

        min_face_px = int(self.config.get("behavior.face_tracking.min_face_size_px", 30))
        min_face_px = max(20, min(200, min_face_px))

        # init targets at center
        yaw_center, pitch_center, yaw_max, pitch_max = self._get_centers_and_limits()
        self._state.yaw_target = yaw_center
        self._state.pitch_target = pitch_center

        last_frame_ts = 0.0

        while self._running:
            t0 = time.time()
            try:
                if not self.camera or not self.camera.is_available():
                    await asyncio.sleep(0.5)
                    continue

                # Presence gating is not wired in this behavior (requires passing SensorManager).
                # Keep config key for compatibility.
                if require_presence:
                    pass

                if bool(self.config.get("behavior.face_tracking.pause_while_speaking", True)):
                    if getattr(self, "_paused", False):
                        await asyncio.sleep(0.1)
                        continue

                # Capture a frame
                frame = await self.camera.capture_frame()
                if frame is None:
                    await asyncio.sleep(interval)
                    continue

                h, w = frame.shape[:2]
                if w < 10 or h < 10:
                    await asyncio.sleep(interval)
                    continue

                # Face detect (grayscale)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.equalizeHist(gray)

                # Scale factor / min neighbors configurable
                scale_factor = float(self.config.get("behavior.face_tracking.scale_factor", 1.2))
                min_neighbors = int(self.config.get("behavior.face_tracking.min_neighbors", 5))
                min_neighbors = max(3, min(10, min_neighbors))
                scale_factor = max(1.05, min(1.5, scale_factor))

                faces = self._cascade.detectMultiScale(
                    gray,
                    scaleFactor=scale_factor,
                    minNeighbors=min_neighbors,
                    flags=cv2.CASCADE_SCALE_IMAGE,
                    minSize=(min_face_px, min_face_px),
                )

                if faces is None or len(faces) == 0:
                    if debug and (t0 - last_log_ts) >= log_every_s:
                        self.logger.info("FaceTracking: faces=0")
                        last_log_ts = t0
                    had_face = False
                    # no face: optionally return to center after timeout
                    if return_to_center_s > 0 and (t0 - self._state.last_seen_ts) > return_to_center_s:
                        yaw_center, pitch_center, yaw_max, pitch_max = self._get_centers_and_limits()
                        self._state.yaw_target = yaw_center
                        self._state.pitch_target = pitch_center
                        await self._move_head(self._state.yaw_target, self._state.pitch_target)
                        self._state.last_seen_ts = t0  # avoid spamming
                    await asyncio.sleep(interval)
                    continue

                # pick largest face (by area)
                x, y, fw, fh = max(faces, key=lambda r: int(r[2]) * int(r[3]))
                cx = x + fw / 2.0
                cy = y + fh / 2.0

                # normalized error (-1..1)
                ex = (cx - (w / 2.0)) / (w / 2.0)
                ey = (cy - (h / 2.0)) / (h / 2.0)

                if abs(ex) < deadzone:
                    ex = 0.0
                if abs(ey) < deadzone:
                    ey = 0.0

                if invert_yaw:
                    ex = -ex
                if invert_pitch:
                    ey = -ey

                yaw_center, pitch_center, yaw_max, pitch_max = self._get_centers_and_limits()
                yaw_new = yaw_center + (ex * yaw_max)
                pitch_new = pitch_center + (ey * pitch_max)

                # Low-pass smooth
                self._state.yaw_target = (alpha * self._state.yaw_target) + ((1.0 - alpha) * yaw_new)
                self._state.pitch_target = (alpha * self._state.pitch_target) + ((1.0 - alpha) * pitch_new)

                self._state.last_seen_ts = t0

                await self._move_head(self._state.yaw_target, self._state.pitch_target)

                # Log when face is detected (throttled). Useful to confirm detection + intended movement.
                if (log_on_face or debug) and (t0 - last_log_ts) >= log_every_s:
                    self.logger.info(
                        "FaceTracking: faces=%d ex=%.2f ey=%.2f yaw=%.1f pitch=%.1f",
                        len(faces),
                        ex,
                        ey,
                        float(self._state.yaw_target),
                        float(self._state.pitch_target),
                    )
                    last_log_ts = t0
                had_face = True

                # pace
                dt = time.time() - t0
                await asyncio.sleep(max(0.0, interval - dt))
                last_frame_ts = t0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                # Don't crash robot on face tracker errors
                self.logger.debug(f"FaceTracking loop error: {e}")
                await asyncio.sleep(0.3)


