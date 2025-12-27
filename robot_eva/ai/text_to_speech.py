"""
Синтез речи через OpenAI TTS API
"""
import logging
import openai
import asyncio
from typing import Optional


class TextToSpeech:
    """Сервис синтеза речи"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = config.get("ai.openai.api_key", "")
        self.model = config.get("ai.text_to_speech.model", "tts-1")
        self.voice = config.get("ai.text_to_speech.voice", "alloy")  # alloy, echo, fable, onyx, nova, shimmer
        self.speed = config.get("ai.text_to_speech.speed", 1.0)
        
        self.client = None
        if self.api_key:
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
            Аудио данные в формате MP3
        """
        if not self.api_key:
            self.logger.warning("OpenAI API ключ не установлен")
            return None
        
        if not text:
            return None
        
        try:
            if not self.client:
                return None
            
            # Вызов OpenAI TTS API
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                speed=self.speed
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
            # Конвертация MP3 в WAV для воспроизведения
            import io
            import pydub
            
            audio_io = io.BytesIO(audio_data)
            audio = pydub.AudioSegment.from_mp3(audio_io)
            wav_io = io.BytesIO()
            audio.export(wav_io, format="wav")
            
            await audio_manager.play_audio(wav_io.getvalue())

