"""
Управление камерой (USB или CSI)
"""
import logging
import asyncio
import cv2
import numpy as np
from typing import Optional, Tuple


class CameraManager:
    """Менеджер камеры (поддержка USB и CSI камер)"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.camera_type = config.get("hardware.camera.type", "usb")  # "usb" или "csi"
        self.camera_index = config.get("hardware.camera.index", 0)
        self.resolution = config.get("hardware.camera.resolution", (640, 480))
        self.fps = config.get("hardware.camera.fps", 30)
        self.rotation = config.get("hardware.camera.rotation", 0)  # 0, 90, 180, 270
        
        self.camera = None
        self.picamera2 = None
        self.is_available_flag = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Инициализация камеры"""
        try:
            if self.camera_type == "csi":
                await self._initialize_csi()
            else:
                await self._initialize_usb()
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации камеры: {e}")
            self.is_available_flag = False
    
    async def _initialize_csi(self):
        """Инициализация CSI камеры (OV5647) через picamera2"""
        try:
            from picamera2 import Picamera2
            
            self.picamera2 = Picamera2(self.camera_index)
            
            # Настройка конфигурации для захвата
            config = self.picamera2.create_still_configuration(
                main={"size": tuple(self.resolution), "format": "RGB888"},
                controls={"FrameRate": self.fps},
                transform=self._get_transform()
            )
            self.picamera2.configure(config)
            self.picamera2.start()
            
            self.is_available_flag = True
            rotation_info = f", поворот: {self.rotation}°" if self.rotation != 0 else ""
            self.logger.info(f"CSI камера инициализирована (разрешение: {self.resolution}, FPS: {self.fps}{rotation_info})")
            
        except ImportError:
            self.logger.error("picamera2 не установлен. Установите: sudo apt install -y python3-picamera2")
            self.is_available_flag = False
        except Exception as e:
            self.logger.error(f"Ошибка инициализации CSI камеры: {e}")
            self.is_available_flag = False
    
    async def _initialize_usb(self):
        """Инициализация USB камеры через OpenCV"""
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
            self.logger.info(f"USB камера инициализирована (разрешение: {self.resolution}, FPS: {self.fps})")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации USB камеры: {e}")
            self.is_available_flag = False
    
    def is_available(self) -> bool:
        """Проверка доступности камеры"""
        if self.camera_type == "csi":
            return self.is_available_flag and self.picamera2 is not None
        else:
            return self.is_available_flag and self.camera is not None and self.camera.isOpened()
    
    def _get_transform(self):
        """Получить трансформацию для поворота изображения"""
        try:
            from libcamera import Transform
            
            # Создаём трансформацию на основе угла поворота
            transform = Transform()
            
            if self.rotation == 180:
                transform.hflip = 1
                transform.vflip = 1
            elif self.rotation == 90:
                transform.hflip = 0
                transform.vflip = 1
                # Для 90/270 нужна транспозиция, но picamera2 это делает автоматически
            elif self.rotation == 270:
                transform.hflip = 1
                transform.vflip = 0
            
            return transform
        except ImportError:
            self.logger.warning("libcamera.Transform недоступен, поворот не применён")
            return None
    
    async def capture_frame(self) -> Optional[np.ndarray]:
        """Захват кадра с камеры"""
        if not self.is_available():
            return None
        
        try:
            async with self._lock:
                if self.camera_type == "csi":
                    # Захват с picamera2 (RGB формат)
                    frame = self.picamera2.capture_array()
                    # Конвертируем RGB в BGR для совместимости с OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    return frame
                else:
                    # Захват с USB камеры
                    ret, frame = self.camera.read()
                    if ret:
                        # Применяем поворот для USB камеры через OpenCV
                        if self.rotation == 90:
                            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                        elif self.rotation == 180:
                            frame = cv2.rotate(frame, cv2.ROTATE_180)
                        elif self.rotation == 270:
                            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
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
        if self.picamera2:
            self.picamera2.stop()
            self.picamera2.close()
            self.is_available_flag = False
            self.logger.info("CSI камера остановлена")
        
        if self.camera:
            self.camera.release()
            self.is_available_flag = False
            self.logger.info("USB камера остановлена")

