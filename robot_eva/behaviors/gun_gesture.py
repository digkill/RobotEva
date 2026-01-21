import asyncio
import logging
import time
import random
from typing import Any, Awaitable, Callable, Optional


class GunGestureBehavior:
    """
    Detect "finger gun" hand gesture using OpenAI Vision (low frequency, debounced).

    Returns:
      triggers on_gun() when gesture is detected N consecutive times.
    """

    def __init__(
        self,
        config: Any,
        camera_manager: Any,
        vision_service: Any,
        *,
        should_run: Callable[[], bool],
        on_gun: Callable[[], Awaitable[None]],
    ):
        self.config = config
        self.camera = camera_manager
        self.vision = vision_service
        self.should_run = should_run
        self.on_gun = on_gun
        self.logger = logging.getLogger(__name__)

        self.enabled: bool = bool(config.get("behavior.gestures.gun.enabled", True))
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False

        self._hits: int = 0
        self._last_trigger_ts: float = 0.0

    async def initialize(self) -> None:
        if not self.enabled:
            self.logger.info("GunGesture: отключен в конфигурации")
            return
        if not self.camera or not getattr(self.camera, "is_available", None) or not self.camera.is_available():
            self.logger.warning("GunGesture: камера недоступна, отключен")
            self.enabled = False
            return
        if not self.vision:
            self.logger.warning("GunGesture: Vision service недоступен, отключен")
            self.enabled = False
            return
        self.logger.info("✅ GunGesture включен (vision-based)")

    async def start(self) -> None:
        if not self.enabled:
            return
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="gesture-gun")

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

    async def _loop(self) -> None:
        interval_s = float(self.config.get("behavior.gestures.gun.interval_seconds", 2.0))
        interval_s = max(0.5, min(15.0, interval_s))
        consecutive = int(self.config.get("behavior.gestures.gun.consecutive_hits", 2))
        consecutive = max(1, min(5, consecutive))
        debounce_s = float(self.config.get("behavior.gestures.gun.debounce_seconds", 10.0))
        debounce_s = max(1.0, min(120.0, debounce_s))

        max_tokens = int(self.config.get("behavior.gestures.gun.max_tokens", 8))
        max_tokens = max(3, min(30, max_tokens))

        prompt = (
            "Look at the image. Is the person making a FINGER GUN gesture? "
            "Gun gestures: index finger pointing forward, thumb up (like a pistol). "
            "Can be with one hand or both hands. "
            "If you see this gesture, reply EXACTLY: GUN. "
            "Otherwise reply EXACTLY: NO. "
            "Be SENSITIVE - detect even casual gun gestures."
        )

        # Небольшая случайная задержка при старте, чтобы жесты не синхронизировались
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        while self._running:
            try:
                await asyncio.sleep(interval_s)
                if not self._running:
                    break

                if not self.should_run():
                    self._hits = 0
                    continue

                if not self.camera or not self.camera.is_available():
                    self._hits = 0
                    continue

                now = time.time()
                if (now - self._last_trigger_ts) < debounce_s:
                    continue

                frame = await self.camera.capture_frame()
                if frame is None:
                    self._hits = 0
                    continue

                # Логируем попытку распознавания
                self.logger.debug(f"GunGesture: проверяю жест...")
                try:
                    txt = await self.vision.describe_scene(frame, prompt=prompt, language="en", max_tokens=max_tokens)
                    ans = (txt or "").strip().upper()
                    # Выводим ответ Vision API для диагностики
                    if ans:
                        self.logger.info(f"GunGesture: Vision API ответил: '{ans}'")
                    else:
                        self.logger.warning(f"GunGesture: Vision API вернул пустой ответ")
                except Exception as e:
                    self.logger.warning(f"GunGesture: ошибка Vision API: {e}")
                    self._hits = 0
                    continue

                is_gun = ans.startswith("GUN")

                if is_gun:
                    self._hits += 1
                    self.logger.info(f"GunGesture: ✅ GUN обнаружен! {self._hits}/{consecutive}")
                else:
                    self._hits = 0
                    self.logger.debug(f"GunGesture: жест не обнаружен (ответ: '{ans}')")

                if self._hits >= consecutive:
                    self._hits = 0
                    self._last_trigger_ts = time.time()
                    self.logger.info("GunGesture: TRIGGER pew-pew reaction")
                    try:
                        await self.on_gun()
                    except Exception as e:
                        self.logger.warning(f"GunGesture: on_gun failed: {e}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.warning(f"GunGesture loop error: {e}")
                await asyncio.sleep(0.5)


