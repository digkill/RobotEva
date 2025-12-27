"""
Распознавание речи через OpenAI Whisper API
"""
import logging
import openai
from typing import Optional


class SpeechToText:
    """Сервис распознавания речи"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = config.get("ai.openai.api_key", "")
        self.model = config.get("ai.speech_to_text.model", "whisper-1")
        self.language = config.get("ai.speech_to_text.language", "ru")
        
        self.client = None
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
    
    async def initialize(self):
        """Инициализация сервиса"""
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен")
        else:
            self.logger.info("Сервис распознавания речи инициализирован")
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Транскрибация аудио в текст
        
        Args:
            audio_data: Аудио данные в формате WAV
            
        Returns:
            Распознанный текст или None
        """
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен")
            return None
        
        try:
            if not self.client:
                return None
            
            import io
            
            # Создание файлового объекта из байтов
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"
            
            # Вызов OpenAI Whisper API
            transcript = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=self.language
            )
            
            text = transcript.text.strip() if hasattr(transcript, 'text') else str(transcript).strip()
            if text:
                self.logger.info(f"Распознано: {text}")
            return text if text else None
            
        except Exception as e:
            self.logger.error(f"Ошибка распознавания речи: {e}")
            return None

