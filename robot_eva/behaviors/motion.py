import asyncio
import logging
import random
from typing import Any, Dict, Optional, Tuple


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class MotionBehavior:
    """
    Lightweight motion/gesture layer that uses the existing servo controller.

    It is designed to be safe:
    - respects configured centers/ranges (and servo controller clamps 0..180)
    - runs as cancellable asyncio tasks
    - prioritizes speaking over idle, and (optionally) over emotion gestures
    """

    def __init__(self, config: Any, servo_controller: Any):
        self.config = config
        self.servos = servo_controller
        self.logger = logging.getLogger(__name__)

        self.enabled: bool = bool(config.get("behavior.motion.enabled", True))
        self.idle_enabled: bool = bool(config.get("behavior.motion.idle.enabled", True))
        self.speaking_enabled: bool = bool(config.get("behavior.motion.speaking.enabled", True))
        self.emotion_enabled: bool = bool(config.get("behavior.motion.emotion.enabled", True))
        self.reset_on_stop: bool = bool(config.get("behavior.motion.reset_on_stop", True))

        # Default centers/ranges (degrees). Can be overridden in config.
        self.center: Dict[int, float] = {
            getattr(self.servos, "SERVO_HEAD_PITCH", 0): float(config.get("behavior.motion.center.head_pitch", 90)),
            getattr(self.servos, "SERVO_HEAD_YAW", 1): float(config.get("behavior.motion.center.head_yaw", 90)),
            getattr(self.servos, "SERVO_NECK_PITCH", 2): float(config.get("behavior.motion.center.neck_pitch", 90)),
            getattr(self.servos, "SERVO_LEFT_ARM", 3): float(config.get("behavior.motion.center.left_arm", 90)),
            getattr(self.servos, "SERVO_RIGHT_ARM", 4): float(config.get("behavior.motion.center.right_arm", 90)),
        }
        self.range: Dict[int, float] = {
            getattr(self.servos, "SERVO_HEAD_PITCH", 0): float(config.get("behavior.motion.range.head_pitch", 15)),
            getattr(self.servos, "SERVO_HEAD_YAW", 1): float(config.get("behavior.motion.range.head_yaw", 25)),
            getattr(self.servos, "SERVO_NECK_PITCH", 2): float(config.get("behavior.motion.range.neck_pitch", 10)),
            getattr(self.servos, "SERVO_LEFT_ARM", 3): float(config.get("behavior.motion.range.left_arm", 20)),
            getattr(self.servos, "SERVO_RIGHT_ARM", 4): float(config.get("behavior.motion.range.right_arm", 20)),
        }

        idle_interval = config.get("behavior.motion.idle.interval_seconds", [8, 16])
        try:
            self.idle_interval_s: Tuple[float, float] = (float(idle_interval[0]), float(idle_interval[1]))
        except Exception:
            self.idle_interval_s = (8.0, 16.0)

        self._running: bool = False
        self._speaking: bool = False
        self._current_emotion: str = "neutral"

        self._idle_task: Optional[asyncio.Task] = None
        self._speaking_task: Optional[asyncio.Task] = None
        self._gesture_task: Optional[asyncio.Task] = None

        self._lock = asyncio.Lock()

    async def initialize(self):
        if not self.enabled:
            return
        if not self.servos:
            self.logger.info("MotionBehavior: servos not available, disabled.")
            self.enabled = False
            return
        self.logger.info(
            "MotionBehavior enabled (idle=%s speaking=%s emotion=%s)",
            self.idle_enabled,
            self.speaking_enabled,
            self.emotion_enabled,
        )

    async def start(self):
        if not self.enabled:
            return
        self._running = True
        if self.idle_enabled and self._idle_task is None:
            self._idle_task = asyncio.create_task(self._idle_loop(), name="motion-idle")

    async def stop(self):
        self._running = False
        await self._cancel_task(self._idle_task)
        await self._cancel_task(self._speaking_task)
        await self._cancel_task(self._gesture_task)
        self._idle_task = None
        self._speaking_task = None
        self._gesture_task = None

        if self.enabled and self.reset_on_stop and self.servos:
            try:
                await self.servos.reset_to_center()
            except Exception:
                pass

    async def notify_emotion(self, emotion: str):
        if not self.enabled or not self.emotion_enabled:
            return
        if not emotion:
            return
        self._current_emotion = (emotion or "neutral").lower()

        # If speaking is active, keep motion stable (speaking loop owns motion).
        if self._speaking and self.speaking_enabled:
            return

        async with self._lock:
            await self._cancel_task(self._gesture_task)
            self._gesture_task = asyncio.create_task(
                self._run_emotion_gesture(self._current_emotion), name="motion-emotion-gesture"
            )

    async def notify_speaking(self, is_speaking: bool):
        if not self.enabled or not self.speaking_enabled:
            return
        async with self._lock:
            self._speaking = bool(is_speaking)
            if self._speaking:
                # Speaking overrides idle and emotion gestures.
                await self._cancel_task(self._gesture_task)
                await self._cancel_task(self._idle_task)
                self._gesture_task = None
                self._idle_task = None
                if self._speaking_task is None:
                    self._speaking_task = asyncio.create_task(self._speaking_loop(), name="motion-speaking")
            else:
                await self._cancel_task(self._speaking_task)
                self._speaking_task = None
                if self._running and self.idle_enabled and self._idle_task is None:
                    self._idle_task = asyncio.create_task(self._idle_loop(), name="motion-idle")

    async def _cancel_task(self, task: Optional[asyncio.Task]):
        if task is None:
            return
        if task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _move_centered(self, servo_id: int, offset: float, smooth: bool = True):
        c = float(self.center.get(servo_id, 90.0))
        r = float(self.range.get(servo_id, 0.0))
        target = _clamp(c + float(offset), c - r, c + r)
        if smooth and hasattr(self.servos, "move_smooth"):
            await self.servos.move_smooth(servo_id, target, steps=6, delay=0.04)
        else:
            await self.servos.move(servo_id, target)

    async def _return_to_center(self, servo_id: int):
        c = float(self.center.get(servo_id, 90.0))
        if hasattr(self.servos, "move_smooth"):
            await self.servos.move_smooth(servo_id, c, steps=6, delay=0.04)
        else:
            await self.servos.move(servo_id, c)

    async def _speaking_loop(self):
        head_yaw = getattr(self.servos, "SERVO_HEAD_YAW", 1)
        head_pitch = getattr(self.servos, "SERVO_HEAD_PITCH", 0)
        left_arm = getattr(self.servos, "SERVO_LEFT_ARM", 3)
        right_arm = getattr(self.servos, "SERVO_RIGHT_ARM", 4)

        arm_enabled = bool(self.config.get("behavior.motion.speaking.arms.enabled", True))
        arm_chance = float(self.config.get("behavior.motion.speaking.arms.chance", 0.55))
        arm_amp = float(self.config.get("behavior.motion.speaking.arms.amplitude", 10))
        arm_amp = max(0.0, min(35.0, arm_amp))

        while self._running and self._speaking:
            try:
                # Small "talking" motion: micro yaw + occasional tiny nod.
                await self._move_centered(head_yaw, random.uniform(-10, 10), smooth=True)
                if random.random() < 0.35:
                    await self._move_centered(head_pitch, random.uniform(-6, 6), smooth=True)

                # Add noticeable arm gestures while speaking (if arms exist).
                # Alternating tiny waves looks "alive" but stays within configured ranges.
                if arm_enabled and random.random() < arm_chance:
                    a = random.uniform(-arm_amp, arm_amp)
                    await self._move_centered(left_arm, a, smooth=True)
                    await self._move_centered(right_arm, -a, smooth=True)
                await asyncio.sleep(random.uniform(0.15, 0.35))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.debug(f"MotionBehavior speaking loop error: {e}")
                await asyncio.sleep(0.3)

        # Return to neutral pose after speaking.
        try:
            await self._return_to_center(head_yaw)
            await self._return_to_center(head_pitch)
            if arm_enabled:
                await self._return_to_center(left_arm)
                await self._return_to_center(right_arm)
        except Exception:
            pass

    async def _idle_loop(self):
        head_yaw = getattr(self.servos, "SERVO_HEAD_YAW", 1)
        head_pitch = getattr(self.servos, "SERVO_HEAD_PITCH", 0)
        left_arm = getattr(self.servos, "SERVO_LEFT_ARM", 3)
        right_arm = getattr(self.servos, "SERVO_RIGHT_ARM", 4)

        lo, hi = self.idle_interval_s
        lo = max(1.0, lo)
        hi = max(lo + 0.1, hi)

        while self._running:
            try:
                if self._speaking:
                    await asyncio.sleep(0.5)
                    continue

                await asyncio.sleep(random.uniform(lo, hi))
                if not self._running or self._speaking:
                    continue

                # Choose a small autonomous gesture.
                roll = random.random()
                if roll < 0.55:
                    # Look around.
                    await self._move_centered(head_yaw, random.uniform(-18, 18), smooth=True)
                    await asyncio.sleep(random.uniform(0.2, 0.6))
                    await self._return_to_center(head_yaw)
                elif roll < 0.8:
                    # Tiny nod.
                    await self._move_centered(head_pitch, random.uniform(-10, 10), smooth=True)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await self._return_to_center(head_pitch)
                else:
                    # Micro arm wiggle (if you have arms connected).
                    await self._move_centered(left_arm, random.uniform(-12, 12), smooth=True)
                    await self._move_centered(right_arm, random.uniform(-12, 12), smooth=True)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await self._return_to_center(left_arm)
                    await self._return_to_center(right_arm)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.debug(f"MotionBehavior idle loop error: {e}")
                await asyncio.sleep(0.6)

    async def _run_emotion_gesture(self, emotion: str):
        """
        Short one-shot gesture per emotion.
        Keep it subtle to avoid annoying repeated motion.
        """
        emotion = (emotion or "neutral").lower()
        head_pitch = getattr(self.servos, "SERVO_HEAD_PITCH", 0)
        head_yaw = getattr(self.servos, "SERVO_HEAD_YAW", 1)

        try:
            if emotion in ("happy",):
                if hasattr(self.servos, "nod_head"):
                    await self.servos.nod_head(times=1)
                else:
                    await self._move_centered(head_pitch, 10, smooth=True)
                    await asyncio.sleep(0.2)
                    await self._return_to_center(head_pitch)

            elif emotion in ("excited",):
                if hasattr(self.servos, "wave_arms"):
                    await self.servos.wave_arms(times=1)
                if hasattr(self.servos, "nod_head"):
                    await self.servos.nod_head(times=1)

            elif emotion in ("surprised",):
                await self._move_centered(head_pitch, 16, smooth=True)
                await asyncio.sleep(0.25)
                await self._return_to_center(head_pitch)

            elif emotion in ("confused",):
                if hasattr(self.servos, "shake_head"):
                    await self.servos.shake_head(times=1)
                else:
                    await self._move_centered(head_yaw, 16, smooth=True)
                    await asyncio.sleep(0.15)
                    await self._move_centered(head_yaw, -16, smooth=True)
                    await asyncio.sleep(0.15)
                    await self._return_to_center(head_yaw)

            elif emotion in ("thinking",):
                # Slight head tilt / pondering movement.
                await self._move_centered(head_yaw, random.uniform(-14, 14), smooth=True)
                await asyncio.sleep(0.35)
                await self._return_to_center(head_yaw)

            elif emotion in ("listening",):
                # Lean forward a touch (attention).
                await self._move_centered(head_pitch, -10, smooth=True)
                await asyncio.sleep(0.25)
                await self._return_to_center(head_pitch)

            elif emotion in ("sleepy", "sad"):
                await self._move_centered(head_pitch, -14, smooth=True)
                await asyncio.sleep(0.35)
                await self._return_to_center(head_pitch)

            else:
                # neutral or unknown: do nothing
                return

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.debug(f"MotionBehavior emotion gesture error ({emotion}): {e}")


