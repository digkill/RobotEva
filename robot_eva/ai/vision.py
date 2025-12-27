"""
Компьютерное зрение для описания того, что видит камера
"""
import logging
import openai
import base64
import cv2
import numpy as np
from typing import Optional


class VisionService:
    """Сервис компьютерного зрения"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = config.get("ai.openai.api_key", "")
        self.model = config.get("ai.vision.model", "gpt-4-vision-preview")
        self.max_tokens = config.get("ai.vision.max_tokens", 300)
        
        self.client = None
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
    
    async def initialize(self):
        """Инициализация сервиса"""
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен для vision")
        else:
            self.logger.info("Сервис компьютерного зрения инициализирован")
    
    async def describe_scene(self, image: Optional[np.ndarray] = None) -> Optional[str]:
        """
        Описание сцены с камеры
        
        Args:
            image: Изображение с камеры (если None, будет захвачено)
            
        Returns:
            Описание сцены
        """
        if not self.api_key:
            return None
        
        try:
            # Получение изображения если не предоставлено
            if image is None:
                from ..hardware.camera import CameraManager
                # Это будет вызвано из основного класса робота
                return None
            
            # Конвертация изображения в base64
            _, buffer = cv2.imencode('.jpg', image)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            if not self.client:
                return None
            
            # Вызов OpenAI Vision API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Опиши подробно, что ты видишь на этом изображении. Будь конкретным и детальным."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens
            )
            
            description = response.choices[0].message.content
            self.logger.info(f"Описание сцены: {description}")
            return description
            
        except Exception as e:
            self.logger.error(f"Ошибка описания сцены: {e}")
            return None
    
    async def recognize_objects(self, image: np.ndarray) -> list:
        """
        Распознавание объектов на изображении
        
        Args:
            image: Изображение
            
        Returns:
            Список распознанных объектов
        """
        description = await self.describe_scene(image)
        if description:
            # Простой парсинг объектов из описания
            # Можно улучшить, используя структурированный вывод
            return [description]
        return []

