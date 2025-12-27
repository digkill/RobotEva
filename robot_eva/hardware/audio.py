"""
Управление аудио (USB микрофон и динамики)
"""
import logging
import asyncio
import pyaudio
import wave
import io
from typing import Optional, Tuple


class AudioManager:
    """Менеджер аудио ввода/вывода"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки аудио
        self.sample_rate = config.get("hardware.audio.sample_rate", 16000)
        self.chunk_size = config.get("hardware.audio.chunk_size", 1024)
        self.channels = config.get("hardware.audio.channels", 1)
        self.format = pyaudio.paInt16
        
        # Настройки устройств
        self.input_device_index = config.get("hardware.audio.input_device", None)
        self.output_device_index = config.get("hardware.audio.output_device", None)
        
        self.audio = None
        self.input_stream = None
        self.output_stream = None
    
    async def initialize(self):
        """Инициализация аудио системы"""
        try:
            self.audio = pyaudio.PyAudio()
            
            # Поиск USB устройств если не указаны
            if self.input_device_index is None:
                self.input_device_index = self._find_usb_microphone()
            
            if self.output_device_index is None:
                self.output_device_index = self._find_usb_speaker()
            
            # Открытие потоков
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.output_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.logger.info(f"Аудио система инициализирована (вход: {self.input_device_index}, выход: {self.output_device_index})")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации аудио: {e}")
            raise
    
    def _find_usb_microphone(self) -> Optional[int]:
        """Поиск USB микрофона"""
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0 and 'usb' in info['name'].lower():
                self.logger.info(f"Найден USB микрофон: {info['name']} (индекс {i})")
                return i
        return None
    
    def _find_usb_speaker(self) -> Optional[int]:
        """Поиск USB динамика"""
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0 and 'usb' in info['name'].lower():
                self.logger.info(f"Найден USB динамик: {info['name']} (индекс {i})")
                return i
        return None
    
    async def record_audio(self, duration: float = 5.0) -> bytes:
        """
        Запись аудио
        
        Args:
            duration: Длительность записи в секундах
            
        Returns:
            Аудио данные в формате WAV
        """
        if not self.input_stream:
            raise RuntimeError("Аудио вход не инициализирован")
        
        frames = []
        num_chunks = int(self.sample_rate / self.chunk_size * duration)
        
        for _ in range(num_chunks):
            data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
            frames.append(data)
            await asyncio.sleep(0)  # Дать возможность другим задачам выполниться
        
        # Сохранение в WAV формат
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        return wav_buffer.getvalue()
    
    async def play_audio(self, audio_data: bytes):
        """
        Воспроизведение аудио
        
        Args:
            audio_data: Аудио данные в формате WAV
        """
        if not self.output_stream:
            raise RuntimeError("Аудио выход не инициализирован")
        
        # Чтение WAV данных
        wav_buffer = io.BytesIO(audio_data)
        with wave.open(wav_buffer, 'rb') as wf:
            chunk = wf.readframes(self.chunk_size)
            while chunk:
                self.output_stream.write(chunk)
                chunk = wf.readframes(self.chunk_size)
                await asyncio.sleep(0)  # Небольшая задержка для других задач
    
    async def play_file(self, file_path: str):
        """Воспроизведение аудио файла"""
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        await self.play_audio(audio_data)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        self.logger.info("Аудио система остановлена")

