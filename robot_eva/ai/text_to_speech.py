"""
Синтез речи через OpenAI TTS API
"""
import logging
import openai
import asyncio
from typing import Optional

from ..utils.http_client import create_httpx_client


class TextToSpeech:
    """Сервис синтеза речи"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = config.get("ai.openai.api_key", "")
        self.model = config.get("ai.text_to_speech.model", "tts-1")
        self.voice = config.get("ai.text_to_speech.voice", "alloy")  # alloy, echo, fable, onyx, nova, shimmer
        # OpenAI TTS speed: 0.25..4.0
        try:
            self.speed = float(config.get("ai.text_to_speech.speed", 1.0))
        except Exception:
            self.speed = 1.0
        self.speed = max(0.25, min(4.0, self.speed))
        
        self.client = None
        if self.api_key:
            # OpenAI SDK uses httpx under the hood; pass a proxy-aware http_client.
            try:
                self.client = openai.OpenAI(api_key=self.api_key, http_client=create_httpx_client(config))
            except TypeError:
                # Fallback for older SDK versions
                self.client = openai.OpenAI(api_key=self.api_key)
    
    async def initialize(self):
        """Инициализация сервиса"""
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен")
        else:
            self.logger.info("Сервис синтеза речи инициализирован")
    
    async def speak(self, text: str) -> Optional[bytes]:
        """
        Синтез речи из текста
        
        Args:
            text: Текст для синтеза
            
        Returns:
            Аудио данные в формате WAV (bytes)
        """
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен")
            return None
        
        if not text:
            return None
        
        try:
            if not self.client:
                return None

            self.logger.info(
                f"TTS request: model={self.model} voice={self.voice} speed={self.speed} text_len={len(text)}"
            )
            
            # Вызов OpenAI TTS API
            response = await asyncio.to_thread(
                self.client.audio.speech.create,
                model=self.model,
                voice=self.voice,
                input=text,
                speed=self.speed,
                # Возвращаем WAV напрямую, чтобы не конвертировать MP3 (Python 3.13: audioop/pyaudioop issues)
                response_format="wav",
            )
            
            # Получение аудио данных
            audio_data = response.content
            
            # Воспроизведение через аудио менеджер
            from ..hardware.audio import AudioManager
            # Это будет вызвано из основного класса робота
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Ошибка синтеза речи: {e}")
            return None
    
    async def generate_and_play(self, text: str, audio_manager):
        """Генерация и воспроизведение речи"""
        audio_data = await self.speak(text)
        if audio_data and audio_manager:
            # Уже WAV (response_format="wav"), можно проигрывать напрямую
            await audio_manager.play_audio(audio_data)

