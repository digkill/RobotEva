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
                # Полноэкранный режим
                self.hdmi_surface = pygame.display.set_mode(
                    self.hdmi_display_size,
                    pygame.FULLSCREEN
                )
                pygame.display.set_caption("Robot Eva")
                pygame.mouse.set_visible(False)  # Скрыть курсор
                self.logger.info(f"HDMI дисплей инициализирован в полноэкранном режиме ({self.hdmi_display_size[0]}x{self.hdmi_display_size[1]})")
            
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
                self.logger.warning(f"Анимация {animation_name} не найдена, используем базовое лицо")
                # Рисуем базовое лицо
                while self.current_animation == animation_name:
                    await self._draw_frame({})  # Пустой frame для базового лица
                    await asyncio.sleep(0.1)
                return
            
            self.logger.info(f"Загрузка анимации: {animation_name}")
            self.logger.info(f"Запущена анимация {animation_name} с {len(frames)} кадрами")
            if len(frames) > 0:
                first_frame = frames[0]
                if "elements" in first_frame:
                    self.logger.info(f"Первый кадр содержит {len(first_frame['elements'])} элементов: {[e.get('type') for e in first_frame['elements']]}")
                else:
                    self.logger.warning("Первый кадр не содержит элементов!")
            
            frame_index = 0
            while self.current_animation == animation_name:
                if frame_index < len(frames):
                    frame = frames[frame_index]
                else:
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
    
    def _debug_draw_simple_face(self):
        """Отладочная функция - простое лицо для проверки"""
        if not self.hdmi_surface:
            return
        
        screen_width, screen_height = self.hdmi_display_size
        center_x = screen_width // 2
        center_y = screen_height // 2
        scale = min(screen_width, screen_height) / 300
        
        # Черный фон
        self.hdmi_surface.fill((0, 0, 0))
        
        # Голова (большой круг)
        head_radius = int(30 * scale)
        pygame.draw.circle(self.hdmi_surface, (200, 220, 240), (center_x, center_y), head_radius)
        
        # Глаза
        eye_radius = int(5 * scale)
        eye_x_offset = int(10 * scale)
        eye_y = center_y - int(5 * scale)
        pygame.draw.circle(self.hdmi_surface, (255, 255, 255), (center_x - eye_x_offset, eye_y), eye_radius)
        pygame.draw.circle(self.hdmi_surface, (255, 255, 255), (center_x + eye_x_offset, eye_y), eye_radius)
        pygame.draw.circle(self.hdmi_surface, (0, 0, 0), (center_x - eye_x_offset, eye_y), max(2, eye_radius // 2))
        pygame.draw.circle(self.hdmi_surface, (0, 0, 0), (center_x + eye_x_offset, eye_y), max(2, eye_radius // 2))
        
        # Рот (улыбка)
        mouth_radius = int(15 * scale)
        mouth_y = center_y + int(10 * scale)
        rect = pygame.Rect(center_x - mouth_radius, mouth_y - mouth_radius, mouth_radius * 2, mouth_radius * 2)
        pygame.draw.arc(self.hdmi_surface, (50, 50, 50), rect, 0, 3.14159, max(4, int(6 * scale)))
        
        pygame.display.flip()
    
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
            # Очистка экрана (темно-синий фон для контраста)
            self.hdmi_surface.fill((20, 30, 40))
            
            # Получение размеров экрана
            screen_width, screen_height = self.hdmi_display_size
            
            # Центрируем лицо робота на экране
            center_x = screen_width // 2
            center_y = screen_height // 2
            
            # Масштаб для координат (координаты относительно центра)
            # Используем примерно 50% меньшей стороны экрана для масштаба
            base_size = min(screen_width, screen_height)
            scale = base_size / 300  # Базовый масштаб
            
            # Отрисовка элементов анимации из frame_data
            elements_to_draw = []
            if frame_data and "elements" in frame_data and len(frame_data["elements"]) > 0:
                elements_to_draw = frame_data["elements"]
                self.logger.info(f"Отрисовка {len(elements_to_draw)} элементов: {[e.get('type') for e in elements_to_draw]}")
            else:
                self.logger.warning(f"Нет элементов в frame_data. frame_data={frame_data}")
            
            # Рисуем элементы анимации
            if elements_to_draw:
                for element in elements_to_draw:
                    element_type = element.get("type", "")
                    
                    if element_type == "body":
                        # Тело робота (большой круг внизу)
                        radius = int(40 * scale)
                        x = center_x + int(element.get("x", 0) * scale)
                        y = center_y + int(element.get("y", 0) * scale)
                        # Градиент для объема
                        pygame.draw.circle(self.hdmi_surface, (80, 130, 180), (x, y), radius)
                        pygame.draw.circle(self.hdmi_surface, (100, 150, 200), (x, y - radius // 3), radius)
                    
                    elif element_type == "head":
                        # Голова робота (большой круг - основное лицо)
                        radius = int(30 * scale)
                        x = center_x + int(element.get("x", 0) * scale)
                        y = center_y + int(element.get("y", 0) * scale)
                        # Основной цвет лица (светло-голубой/белый)
                        pygame.draw.circle(self.hdmi_surface, (200, 220, 240), (x, y), radius)
                        # Обводка
                        pygame.draw.circle(self.hdmi_surface, (150, 180, 220), (x, y), radius, 3)
                    
                    elif element_type in ["eye_left", "eye_right"]:
                        # Глаза робота
                        base_radius = int(5 * scale)
                        radius = max(int(3 * scale), int(element.get("radius", base_radius) * scale))
                        x = center_x + int(element.get("x", 0) * scale)
                        y = center_y + int(element.get("y", 0) * scale)
                        
                        shape = element.get("shape", "circle")
                        if shape == "circle":
                            # Белый глаз с черным зрачком
                            pygame.draw.circle(self.hdmi_surface, (255, 255, 255), (x, y), radius)
                            pygame.draw.circle(self.hdmi_surface, (0, 0, 0), (x, y), max(2, radius // 2))
                        elif shape == "ellipse":
                            # Улыбающиеся глаза (эллипс)
                            width = int(element.get("width", 8) * scale)
                            height = int(element.get("height", 4) * scale)
                            pygame.draw.ellipse(
                                self.hdmi_surface,
                                (255, 255, 255),
                                (x - width // 2, y - height // 2, width, height)
                            )
                            # Зрачок
                            pygame.draw.circle(self.hdmi_surface, (0, 0, 0), (x, y), max(2, min(width, height) // 3))
                        elif shape == "line":
                            # Закрытые глаза (линия)
                            width = int(element.get("width", 8) * scale)
                            line_width = max(2, int(3 * scale))
                            pygame.draw.line(
                                self.hdmi_surface,
                                (100, 100, 100),
                                (x - width // 2, y),
                                (x + width // 2, y),
                                line_width
                            )
                    
                    elif element_type == "mouth":
                        # Рот робота
                        shape = element.get("shape", "arc")
                        x = center_x + int(element.get("x", 0) * scale)
                        y = center_y + int(element.get("y", 0) * scale)
                        radius = int(element.get("radius", 15) * scale)
                        
                        if shape == "arc":
                            # Улыбка (дуга вверх) или грусть (дуга вниз)
                            start_angle = element.get("start", 0) * 3.14159 / 180
                            end_angle = element.get("end", 180) * 3.14159 / 180
                            # Рисуем дугу
                            rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
                            line_width = max(4, int(6 * scale))
                            pygame.draw.arc(
                                self.hdmi_surface,
                                (50, 50, 50),
                                rect,
                                start_angle,
                                end_angle,
                                line_width
                            )
                        elif shape == "ellipse":
                            # Удивленный рот (овал)
                            width = int(element.get("width", 20) * scale)
                            height = int(element.get("height", 15) * scale)
                            line_width = max(3, int(4 * scale))
                            pygame.draw.ellipse(
                                self.hdmi_surface,
                                (50, 50, 50),
                                (x - width // 2, y - height // 2, width, height),
                                line_width
                            )
                        elif shape == "line":
                            # Нейтральный рот (прямая линия)
                            width = int(element.get("width", 15) * scale)
                            line_width = max(3, int(5 * scale))
                            pygame.draw.line(
                                self.hdmi_surface,
                                (50, 50, 50),
                                (x - width // 2, y),
                                (x + width // 2, y),
                                line_width
                            )
            else:
                # Если нет элементов, рисуем базовое лицо
                self.logger.debug("Нет элементов в frame_data, рисуем базовое лицо")
                # Голова робота
                head_radius = int(30 * scale)
                pygame.draw.circle(self.hdmi_surface, (200, 220, 240), (center_x, center_y), head_radius)
                pygame.draw.circle(self.hdmi_surface, (150, 180, 220), (center_x, center_y), head_radius, max(2, int(3 * scale)))
                
                # Глаза
                eye_radius = int(5 * scale)
                eye_x_offset = int(10 * scale)
                eye_y = center_y - int(5 * scale)
                pygame.draw.circle(self.hdmi_surface, (255, 255, 255), (center_x - eye_x_offset, eye_y), eye_radius)
                pygame.draw.circle(self.hdmi_surface, (255, 255, 255), (center_x + eye_x_offset, eye_y), eye_radius)
                pygame.draw.circle(self.hdmi_surface, (0, 0, 0), (center_x - eye_x_offset, eye_y), max(2, eye_radius // 2))
                pygame.draw.circle(self.hdmi_surface, (0, 0, 0), (center_x + eye_x_offset, eye_y), max(2, eye_radius // 2))
                
                # Рот
                mouth_radius = int(15 * scale)
                mouth_y = center_y + int(10 * scale)
                rect = pygame.Rect(center_x - mouth_radius, mouth_y - mouth_radius, mouth_radius * 2, mouth_radius * 2)
                pygame.draw.arc(self.hdmi_surface, (50, 50, 50), rect, 0, 3.14159, max(4, int(6 * scale)))
            
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

