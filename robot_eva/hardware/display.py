"""
Управление дисплеями:
- HDMI (pygame, fullscreen)
- 2.8" (SPI/Framebuffer backend)

Важно: pygame создаёт ОДНО окно. Поэтому 2.8" дисплей должен быть отдельным backend (SPI),
а не вторым `pygame.display.set_mode()`.
"""

import asyncio
import logging
import os
import random
from typing import Optional, Tuple

import pygame
from PIL import Image

from .display_small_spi import SmallDisplayBase
from .display_small_fbdev import SmallFbdevDisplay
from .display_small_sdl import SmallSdlDisplay
from ..emotions.face_renderer import render_face_frame


class DisplayManager:
    """Менеджер дисплеев робота"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 2.8" дисплей
        self.small_display_enabled = config.get("hardware.display.small.enabled", True)
        self.small_display_size = tuple(config.get("hardware.display.small.size", (320, 240)))

        # HDMI дисплей
        self.hdmi_display_enabled = config.get("hardware.display.hdmi.enabled", True)
        self.hdmi_display_size = tuple(config.get("hardware.display.hdmi.size", (1920, 1080)))

        self.small_display: Optional[SmallDisplayBase] = None
        self.hdmi_surface: Optional[pygame.Surface] = None

        self.current_animation: Optional[str] = None
        self.animation_task: Optional[asyncio.Task] = None

        # Speaking overlay (mouth animation while robot is talking)
        self._speaking: bool = False
        
        # Touch animations - читаем из config или используем все по умолчанию
        touch_enabled = config.get("hardware.display.small.touch.enabled", True)
        configured_animations = config.get("hardware.display.small.touch.animations", [])
        
        default_animations = [
            "dizzy", "stars", "hearts", "silly", "crazy", "sparkle", 
            "laugh", "blush", "surprise_big", "money"
        ]
        
        self._touch_enabled = touch_enabled
        self._touch_animations = configured_animations if configured_animations else default_animations
        self._previous_animation: Optional[str] = None  # Для возврата после touch анимации

    async def set_speaking(self, is_speaking: bool) -> None:
        """Enable/disable speaking overlay animation (mouth movement)."""
        self._speaking = bool(is_speaking)
        # Ensure animation loop is running so the mouth can animate.
        if self._speaking:
            try:
                if not self.current_animation or self.animation_task is None or self.animation_task.done():
                    await self.show_animation("neutral")
            except Exception:
                pass

    async def initialize(self):
        """Инициализация дисплеев"""
        # 2.8" small display
        if self.small_display_enabled:
            try:
                backend = str(self.config.get("hardware.display.small.backend", "fbdev")).lower()
                # Auto-pick: if running under desktop, prefer SDL overlay; otherwise use fbdev.
                if backend == "auto":
                    backend = "sdl" if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) else "fbdev"

                if backend == "fbdev":
                    self.small_display = SmallFbdevDisplay(self.config, self.small_display_size)
                elif backend == "sdl":
                    self.small_display = SmallSdlDisplay(self.config, self.small_display_size)
                else:
                    raise RuntimeError(f"Unsupported small display backend: {backend}")
                await self.small_display.initialize()
                
                # Установить callback для touch событий (только для SDL)
                if isinstance(self.small_display, SmallSdlDisplay):
                    self.small_display.set_touch_callback(self._handle_touch)
                
                self.logger.info(f'2.8" дисплей инициализирован ({self.small_display_size[0]}x{self.small_display_size[1]})')
            except Exception as e:
                self.logger.warning(f'Не удалось инициализировать 2.8" дисплей: {e}')
                self.small_display = None

        # HDMI (pygame)
        if self.hdmi_display_enabled:
            try:
                pygame.init()
                self.hdmi_surface = pygame.display.set_mode(self.hdmi_display_size, pygame.FULLSCREEN)
                pygame.display.set_caption("Robot Eva")
                pygame.mouse.set_visible(False)
                self.logger.info(f"HDMI дисплей инициализирован ({self.hdmi_display_size[0]}x{self.hdmi_display_size[1]})")
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать HDMI дисплей: {e}")
                self.hdmi_surface = None

    async def show_animation(self, animation_name: str):
        """Показ анимации на дисплеях"""
        self.logger.info(f"show_animation: {animation_name} (small={self.small_display is not None}, hdmi={self.hdmi_surface is not None})")
        if self.animation_task:
            self.animation_task.cancel()

        self.current_animation = animation_name
        self.animation_task = asyncio.create_task(self._run_animation(animation_name))

    async def _run_animation(self, animation_name: str):
        """Запуск анимации"""
        from ..emotions.animations import get_animation_frame, get_animation_info

        try:
            active_name = animation_name
            info = get_animation_info(active_name)
            self.logger.debug(f"_run_animation: {active_name} starting (frames={info.get('frames')}, loop={info.get('loop')})")
            loop = bool(info.get("loop", True))
            num_frames = int(info.get("frames", 1)) or 1

            # Random blink scheduler (more natural & less predictable)
            blink_min = int(self.config.get("emotions.blink.min_interval_frames", 90))  # ~7.2s at 12.5fps
            blink_max = int(self.config.get("emotions.blink.max_interval_frames", 180))  # ~14.4s
            blink_duration = int(self.config.get("emotions.blink.duration_frames", 2))
            blink_min = max(10, blink_min)
            blink_max = max(blink_min, blink_max)
            blink_duration = max(1, blink_duration)

            next_blink_at = random.randint(blink_min, blink_max)
            blink_remaining = 0

            frame_index = 0  # absolute counter
            while True:
                # Stop if someone changed the animation externally.
                if self.current_animation != active_name:
                    break

                if not loop and frame_index >= num_frames:
                    # One-shot animation finished -> transition to neutral WITHOUT stopping the render loop.
                    active_name = "neutral"
                    self.current_animation = "neutral"
                    info = get_animation_info(active_name)
                    loop = bool(info.get("loop", True))
                    num_frames = int(info.get("frames", 1)) or 1
                    continue

                frame = get_animation_frame(active_name, frame_index)
                blink_active = False
                if blink_remaining > 0:
                    blink_active = True
                    blink_remaining -= 1
                elif frame_index >= next_blink_at:
                    blink_remaining = blink_duration
                    next_blink_at = frame_index + random.randint(blink_min, blink_max)
                    blink_active = True
                    blink_remaining -= 1

                await self._draw_frame(frame, blink_active=blink_active, absolute_frame_idx=frame_index)
                frame_index += 1
                await asyncio.sleep(0.08)  # ~12.5 FPS
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Ошибка в анимации: {e}", exc_info=True)

    async def _draw_frame(self, frame_data: dict, blink_active: bool = False, absolute_frame_idx: Optional[int] = None):
        # Рендерим один раз в PIL и отдаем в оба выхода
        # (чтобы визуал был одинаковый “под Eilik”)
        # Глобальные сдвиги элементов лица (в условных единицах анимации, до масштабирования)
        # Положительный y_offset -> ниже на экране.
        try:
            eye_y_offset = float(self.config.get("emotions.face.eye_y_offset", 0.0))
        except Exception:
            eye_y_offset = 0.0
        try:
            mouth_y_offset = float(self.config.get("emotions.face.mouth_y_offset", 0.0))
        except Exception:
            mouth_y_offset = 0.0

        if isinstance(frame_data, dict):
            # Always attach offsets (even 0.0) so behavior is predictable.
            frame_data = dict(frame_data)  # don't mutate upstream
            frame_data["_face_offsets"] = {"eye_y": eye_y_offset, "mouth_y": mouth_y_offset}

            # Apply blink by forcing eyes into "line" shape for a few frames (if not already sleepy)
            if blink_active:
                els = frame_data.get("elements")
                if isinstance(els, list):
                    new_els = []
                    for e in els:
                        if isinstance(e, dict) and e.get("type") in ("eye_left", "eye_right") and e.get("shape") != "line":
                            ee = dict(e)
                            ee["shape"] = "line"
                            ee["width"] = e.get("width", 70)
                            new_els.append(ee)
                        else:
                            new_els.append(e)
                    frame_data["elements"] = new_els

            # Speaking overlay: animate mouth while robot is talking.
            # This is intentionally simple (open/close), but looks much more "alive".
            if self._speaking and bool(self.config.get("emotions.speaking.enabled", True)):
                els = frame_data.get("elements")
                if isinstance(els, list):
                    period = int(self.config.get("emotions.speaking.period_frames", 2))  # ~6.25 Hz at 12.5fps
                    period = max(1, period)
                    idx = int(absolute_frame_idx) if absolute_frame_idx is not None else int(frame_data.get("frame", 0))
                    mouth_open = ((idx // period) % 2) == 0

                    open_w = float(self.config.get("emotions.speaking.open_width", 52))
                    open_h = float(self.config.get("emotions.speaking.open_height", 34))
                    closed_w = float(self.config.get("emotions.speaking.closed_width", 58))

                    new_els = []
                    for e in els:
                        if isinstance(e, dict) and e.get("type") == "mouth":
                            ee = dict(e)
                            # Preserve x/y, but override shape params to emulate talking.
                            if mouth_open:
                                ee["shape"] = "ellipse"
                                ee["width"] = open_w
                                ee["height"] = open_h
                            else:
                                ee["shape"] = "line"
                                ee["width"] = closed_w
                            new_els.append(ee)
                        else:
                            new_els.append(e)
                    frame_data["elements"] = new_els

        pil_small = render_face_frame(frame_data, self.small_display_size)
        pil_hdmi = render_face_frame(frame_data, self.hdmi_display_size)

        if self.small_display:
            await self.small_display.display(pil_small)

        if self.hdmi_surface:
            await self._display_pil_on_hdmi(pil_hdmi)

    async def _display_pil_on_hdmi(self, img: Image.Image):
        try:
            if img.mode != "RGB":
                img = img.convert("RGB")
            surf = pygame.image.fromstring(img.tobytes(), img.size, "RGB")
            self.hdmi_surface.blit(surf, (0, 0))
            pygame.display.flip()
        except Exception as e:
            self.logger.error(f"Ошибка отрисовки на HDMI: {e}", exc_info=True)
    
    async def _handle_touch(self, pos: Tuple[int, int]) -> None:
        """Обработка касания экрана - показать случайную забавную анимацию"""
        try:
            # Проверяем, включены ли touch анимации
            if not self._touch_enabled:
                return
            
            x, y = pos
            self.logger.info(f"Touch detected at ({x}, {y})")
            
            # Выбираем случайную touch анимацию
            if not self._touch_animations:
                return
            
            touch_animation = random.choice(self._touch_animations)
            self.logger.info(f"Playing touch animation: {touch_animation}")
            
            # Сохраняем текущую анимацию для возврата
            self._previous_animation = self.current_animation
            
            # Показываем touch анимацию
            await self.show_animation(touch_animation)
            
            # После окончания анимации возвращаемся к предыдущей
            # (show_animation уже ждёт завершения если loop=False)
            if self._previous_animation:
                await asyncio.sleep(0.3)  # Небольшая пауза
                await self.show_animation(self._previous_animation)
            
        except Exception as e:
            self.logger.error(f"Touch handling error: {e}", exc_info=True)

    async def cleanup(self):
        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass

        if self.small_display:
            try:
                await self.small_display.cleanup()
            except Exception:
                pass
            self.small_display = None

        if self.hdmi_surface:
            try:
                pygame.quit()
            except Exception:
                pass
            self.hdmi_surface = None

        self.logger.info("Дисплеи остановлены")

