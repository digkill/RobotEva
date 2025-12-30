"""
Управление USB камерой
"""
import logging
import asyncio
import cv2
import numpy as np
from typing import Optional, Tuple


class CameraManager:
    """Менеджер USB камеры"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.camera_index = config.get("hardware.camera.index", 0)
        self.resolution = config.get("hardware.camera.resolution", (640, 480))
        self.fps = config.get("hardware.camera.fps", 30)
        
        self.camera: Optional[cv2.VideoCapture] = None
        self.is_available_flag = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Инициализация камеры"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                self.logger.warning(f"Не удалось открыть камеру {self.camera_index}")
                self.is_available_flag = False
                return
            
            # Установка параметров
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            self.is_available_flag = True
            self.logger.info(f"Камера инициализирована (разрешение: {self.resolution}, FPS: {self.fps})")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации камеры: {e}")
            self.is_available_flag = False
    
    def is_available(self) -> bool:
        """Проверка доступности камеры"""
        return self.is_available_flag and self.camera is not None and self.camera.isOpened()
    
    async def capture_frame(self) -> Optional[np.ndarray]:
        """Захват кадра с камеры"""
        if not self.is_available():
            return None
        
        try:
            async with self._lock:
                ret, frame = self.camera.read()
                if ret:
                    return frame
                return None
        except Exception as e:
            self.logger.error(f"Ошибка захвата кадра: {e}")
            return None
    
    async def save_frame(self, file_path: str) -> bool:
        """Сохранение кадра в файл"""
        frame = await self.capture_frame()
        if frame is not None:
            cv2.imwrite(file_path, frame)
            return True
        return False
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.camera:
            self.camera.release()
            self.is_available_flag = False
            self.logger.info("Камера остановлена")

