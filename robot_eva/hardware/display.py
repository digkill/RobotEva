"""
Управление дисплеями (2.8" и HDMI)
"""
import logging
import asyncio
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import pygame


class DisplayManager:
    """Менеджер дисплеев робота"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки 2.8" дисплея
        self.small_display_enabled = config.get("hardware.display.small.enabled", True)
        self.small_display_size = config.get("hardware.display.small.size", (320, 240))
        self.small_display_spi = config.get("hardware.display.small.spi", {})
        
        # Настройки HDMI дисплея
        self.hdmi_display_enabled = config.get("hardware.display.hdmi.enabled", True)
        self.hdmi_display_size = config.get("hardware.display.hdmi.size", (1920, 1080))
        
        self.small_display = None
        self.hdmi_surface = None
        self.current_animation = None
        self.animation_task = None
    
    async def initialize(self):
        """Инициализация дисплеев"""
        try:
            # Инициализация 2.8" дисплея (если используется SPI)
            if self.small_display_enabled:
                # Здесь можно добавить инициализацию конкретного дисплея
                # Например, для ST7789 или ILI9341
                self.logger.info("2.8\" дисплей инициализирован")
            
            # Инициализация HDMI дисплея через pygame
            if self.hdmi_display_enabled:
                pygame.init()
                self.hdmi_surface = pygame.display.set_mode(self.hdmi_display_size)
                pygame.display.set_caption("Robot Eva")
                self.logger.info("HDMI дисплей инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации дисплеев: {e}")
            raise
    
    async def show_animation(self, animation_name: str):
        """Показ анимации на дисплеях"""
        if self.animation_task:
            self.animation_task.cancel()
        
        self.current_animation = animation_name
        self.animation_task = asyncio.create_task(self._run_animation(animation_name))
    
    async def _run_animation(self, animation_name: str):
        """Запуск анимации"""
        try:
            # Загрузка анимации из модуля эмоций
            from ..emotions.animations import get_animation_frames
            
            frames = get_animation_frames(animation_name)
            if not frames:
                self.logger.warning(f"Анимация {animation_name} не найдена")
                return
            
            frame_index = 0
            while self.current_animation == animation_name:
                frame = frames[frame_index % len(frames)]
                await self._draw_frame(frame)
                
                frame_index += 1
                await asyncio.sleep(0.1)  # ~10 FPS
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Ошибка в анимации: {e}")
    
    async def _draw_frame(self, frame_data: dict):
        """Отрисовка кадра анимации"""
        # Создание изображения для анимации
        if self.small_display_enabled:
            await self._draw_small_display(frame_data)
        
        if self.hdmi_display_enabled:
            await self._draw_hdmi_display(frame_data)
    
    async def _draw_small_display(self, frame_data: dict):
        """Отрисовка на 2.8" дисплее"""
        # Здесь будет код для отрисовки на SPI дисплее
        # Пока заглушка
        pass
    
    async def _draw_hdmi_display(self, frame_data: dict):
        """Отрисовка на HDMI дисплее"""
        if not self.hdmi_surface:
            return
        
        try:
            # Очистка экрана
            self.hdmi_surface.fill((0, 0, 0))
            
            # Отрисовка элементов анимации
            # Здесь можно добавить отрисовку робота, эмоций и т.д.
            
            pygame.display.flip()
        except Exception as e:
            self.logger.error(f"Ошибка отрисовки на HDMI: {e}")
    
    async def show_text(self, text: str, duration: float = 3.0):
        """Показ текста на дисплеях"""
        # Создание изображения с текстом
        if self.hdmi_display_enabled and self.hdmi_surface:
            font = pygame.font.Font(None, 72)
            text_surface = font.render(text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(self.hdmi_display_size[0]//2, self.hdmi_display_size[1]//2))
            
            self.hdmi_surface.fill((0, 0, 0))
            self.hdmi_surface.blit(text_surface, text_rect)
            pygame.display.flip()
            
            await asyncio.sleep(duration)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
        
        if self.hdmi_display_enabled:
            pygame.quit()
        
        self.logger.info("Дисплеи остановлены")

