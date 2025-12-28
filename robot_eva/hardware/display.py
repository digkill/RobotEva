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
        if self.animation_task:
            self.animation_task.cancel()

        self.current_animation = animation_name
        self.animation_task = asyncio.create_task(self._run_animation(animation_name))

    async def _run_animation(self, animation_name: str):
        """Запуск анимации"""
        from ..emotions.animations import get_animation_frame, get_animation_info

        try:
            info = get_animation_info(animation_name)
            loop = bool(info.get("loop", True))
            num_frames = int(info.get("frames", 1)) or 1

            frame_index = 0  # absolute counter (needed for stable blink rate)
            while self.current_animation == animation_name:
                if not loop and frame_index >= num_frames:
                    # одноразовая анимация завершена — возвращаемся в нейтраль
                    self.current_animation = "neutral"
                    break

                frame = get_animation_frame(animation_name, frame_index)
                await self._draw_frame(frame)
                frame_index += 1
                await asyncio.sleep(0.08)  # ~12.5 FPS
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Ошибка в анимации: {e}", exc_info=True)

    async def _draw_frame(self, frame_data: dict):
        # Рендерим один раз в PIL и отдаем в оба выхода
        # (чтобы визуал был одинаковый “под Eilik”)
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

