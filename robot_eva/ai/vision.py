"""
Компьютерное зрение для описания того, что видит камера
"""
import logging
import openai
import asyncio
import base64
import cv2
import numpy as np
from typing import Optional

from ..utils.http_client import create_httpx_client


class VisionService:
    """Сервис компьютерного зрения"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = config.get("ai.openai.api_key", "")
        # gpt-4-vision-preview was deprecated; use a modern multimodal model.
        self.model = config.get("ai.vision.model", "gpt-4o-mini")
        self.max_tokens = config.get("ai.vision.max_tokens", 300)
        
        self.client = None
        if self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key, http_client=create_httpx_client(config))
            except TypeError:
                self.client = openai.OpenAI(api_key=self.api_key)
    
    async def initialize(self):
        """Инициализация сервиса"""
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен для vision")
        else:
            self.logger.info("Сервис компьютерного зрения инициализирован")

    def _normalize_lang(self, lang: Optional[str]) -> str:
        l = (lang or "").strip().lower()
        if not l or l == "auto":
            l = (self.config.get("ai.language.default", "") or "").strip().lower() or "ru"
        if l not in ("ru", "en", "th"):
            l = "ru"
        return l

    def _default_prompt(self, lang: str) -> str:
        if lang == "en":
            return "Describe in detail what you see in this image. Be specific and concrete."
        if lang == "th":
            return "อธิบายอย่างละเอียดว่าคุณเห็นอะไรในภาพนี้ โดยเฉพาะเจาะจงและเป็นรูปธรรม"
        return "Опиши подробно, что ты видишь на этом изображении. Будь конкретным и детальным."

    async def describe_scene(
        self,
        image: Optional[np.ndarray] = None,
        *,
        prompt: Optional[str] = None,
        language: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
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

            lang = self._normalize_lang(language)
            prompt_text = (prompt or "").strip() or str(self.config.get("ai.vision.prompt", "") or "").strip()
            if not prompt_text:
                prompt_text = self._default_prompt(lang)
            mt = int(max_tokens if max_tokens is not None else self.max_tokens)
            
            # Вызов OpenAI Vision API
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text
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
                max_tokens=mt,
            )
            
            description = response.choices[0].message.content
            # Avoid spamming logs for classifier-like prompts (gestures return NO/HEART/GUN).
            d = (description or "").strip()
            p = (prompt_text or "").strip().lower()
            if ("reply with exactly" in p) or ("reply with exactly:" in p):
                self.logger.debug(f"Vision classify: {d}")
            else:
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

