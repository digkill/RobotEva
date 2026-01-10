"""
Small display backend via SDL/pygame fullscreen window.

Use this when Raspberry Pi runs a desktop (X11/Wayland) and you want the animation
to appear over the desktop on the DSI panel.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional, Tuple, Callable, Awaitable

import pygame
from PIL import Image

from .display_small_spi import SmallDisplayBase


class SmallSdlDisplay(SmallDisplayBase):
    def __init__(self, config, logical_size: Tuple[int, int]):
        self.config = config
        self.logical_size = (int(logical_size[0]), int(logical_size[1]))
        self.rotation = int(config.get("hardware.display.small.rotation", 0))
        self.logger = logging.getLogger(__name__)

        self._surface: Optional[pygame.Surface] = None
        self._window_size: Optional[Tuple[int, int]] = None
        
        # Touch callback
        self._touch_callback: Optional[Callable[[Tuple[int, int]], Awaitable[None]]] = None

    async def initialize(self) -> None:
        # Require GUI session
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            raise RuntimeError("SDL backend requires desktop session (DISPLAY/WAYLAND_DISPLAY not set)")

        pygame.init()

        info = pygame.display.Info()
        w, h = int(getattr(info, "current_w", self.logical_size[0])), int(getattr(info, "current_h", self.logical_size[1]))
        self._window_size = (w, h)

        self._surface = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
        pygame.display.set_caption("Robot Eva - DSI")
        pygame.mouse.set_visible(False)

        # Clear once
        self._surface.fill((0, 0, 0))
        pygame.display.flip()

    async def display(self, img: Image.Image) -> None:
        if not self._surface or not self._window_size:
            return

        # Process touch/mouse events
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pass  # Игнорируем закрытие в fullscreen
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                    # Получаем координаты касания
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        touch_x, touch_y = event.pos
                    else:  # FINGERDOWN (touchscreen)
                        # Нормализованные координаты (0-1)
                        touch_x = int(event.x * self._window_size[0])
                        touch_y = int(event.y * self._window_size[1])
                    
                    # Вызываем callback если установлен
                    if self._touch_callback:
                        try:
                            await self._touch_callback((touch_x, touch_y))
                        except Exception as e:
                            self.logger.error(f"Touch callback error: {e}")
        except Exception as e:
            self.logger.debug(f"Event processing error: {e}")

        if img.mode != "RGB":
            img = img.convert("RGB")

        # Render at logical size first
        if img.size != self.logical_size:
            img = img.resize(self.logical_size)

        # Apply rotation (degrees)
        rot = self.rotation % 360
        if rot:
            img = img.rotate(rot, expand=True)

        # Fit into window, centered (letterbox)
        win_w, win_h = self._window_size
        canvas = Image.new("RGB", (win_w, win_h), (0, 0, 0))
        x = (win_w - img.size[0]) // 2
        y = (win_h - img.size[1]) // 2
        canvas.paste(img, (x, y))

        surf = pygame.image.fromstring(canvas.tobytes(), canvas.size, "RGB")
        self._surface.blit(surf, (0, 0))
        pygame.display.flip()

        # Yield back to event loop
        await asyncio.sleep(0)
    
    def set_touch_callback(self, callback: Optional[Callable[[Tuple[int, int]], Awaitable[None]]]) -> None:
        """Установить callback для обработки касаний экрана"""
        self._touch_callback = callback

    async def cleanup(self) -> None:
        try:
            pygame.quit()
        except Exception:
            pass
        self._surface = None
        self._window_size = None



