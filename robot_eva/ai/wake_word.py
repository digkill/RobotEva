"""
Обнаружение wake word через Porcupine
"""
import logging
import os
import pvporcupine
from pvrecorder import PvRecorder
import asyncio
from typing import Optional


class WakeWordDetector:
    """Детектор wake word "Hey Eve" """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.model_path = config.get(
            "ai.wake_word.model_path",
            "/home/pi/Projects/RobotEva/models/Hey-Eva_en_raspberry-pi_v4_0_0.ppn"
        )
        self.access_key = config.get("ai.wake_word.access_key", "")
        
        self.porcupine: Optional[pvporcupine.Porcupine] = None
        self.recorder: Optional[PvRecorder] = None
        self.is_detecting = False
    
    async def initialize(self):
        """Инициализация детектора wake word"""
        if not self.access_key:
            self.logger.warning("Porcupine access key не установлен, wake word детектор отключен")
            self.porcupine = None
            self.recorder = None
            return
        
        if not os.path.exists(self.model_path):
            self.logger.warning(f"Файл модели wake word не найден: {self.model_path}")
            self.porcupine = None
            self.recorder = None
            return
        
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.model_path]
            )
            
            self.recorder = PvRecorder(
                device_index=-1,  # Использовать устройство по умолчанию
                frame_length=self.porcupine.frame_length
            )
            
            self.logger.info("Wake word детектор инициализирован")
            
        except Exception as e:
            self.logger.warning(f"Ошибка инициализации wake word детектора: {e}")
            self.logger.warning("Wake word детектор отключен, робот будет работать без активации по голосу")
            self.porcupine = None
            self.recorder = None
    
    async def detect(self) -> bool:
        """
        Проверка наличия wake word
        
        Returns:
            True если wake word обнаружен
        """
        if not self.porcupine or not self.recorder:
            return False
        
        try:
            if not self.recorder.is_recording:
                self.recorder.start()
            
            pcm = self.recorder.read()
            keyword_index = self.porcupine.process(pcm)
            
            if keyword_index >= 0:
                self.logger.info("Wake word обнаружен!")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении wake word: {e}")
            return False
    
    async def start_listening(self):
        """Начало непрерывного прослушивания"""
        self.is_detecting = True
        if self.recorder and not self.recorder.is_recording:
            self.recorder.start()
    
    async def stop_listening(self):
        """Остановка прослушивания"""
        self.is_detecting = False
        if self.recorder and self.recorder.is_recording:
            self.recorder.stop()
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.recorder:
            if self.recorder.is_recording:
                self.recorder.stop()
            self.recorder.delete()
        
        if self.porcupine:
            self.porcupine.delete()
        
        self.logger.info("Wake word детектор остановлен")

