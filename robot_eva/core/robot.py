"""
Главный класс робота Eva
"""
import asyncio
import logging
from typing import Optional
from .config import Config
from ..hardware.servos import ServoController
from ..hardware.display import DisplayManager
from ..hardware.audio import AudioManager
from ..hardware.camera import CameraManager
from ..hardware.sensors import SensorManager
from ..hardware.led import LEDController
from ..ai.wake_word import WakeWordDetector
from ..ai.speech_to_text import SpeechToText
from ..ai.text_to_speech import TextToSpeech
from ..ai.llm import LLMService
from ..ai.vision import VisionService
from ..emotions.emotion_engine import EmotionEngine
from ..services.smart_home import SmartHomeService
from ..services.internet import InternetService
from ..services.media import MediaService


class RobotEva:
    """Главный класс робота-ассистента Eva"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Инициализация компонентов
        self.servo_controller = None
        self.display_manager = None
        self.audio_manager = None
        self.camera_manager = None
        self.sensor_manager = None
        self.led_controller = None
        self.wake_word_detector = None
        self.speech_to_text = None
        self.text_to_speech = None
        self.llm_service = None
        self.vision_service = None
        self.emotion_engine = None
        self.smart_home_service = None
        self.internet_service = None
        self.media_service = None
        
        self.is_running = False
        self.is_listening = False
    
    async def initialize(self):
        """Инициализация всех компонентов робота"""
        self.logger.info("Инициализация робота Eva...")
        
        try:
            # Инициализация железа
            self.servo_controller = ServoController(self.config)
            await self.servo_controller.initialize()
            
            self.display_manager = DisplayManager(self.config)
            await self.display_manager.initialize()
            
            self.audio_manager = AudioManager(self.config)
            await self.audio_manager.initialize()
            
            self.camera_manager = CameraManager(self.config)
            await self.camera_manager.initialize()
            
            self.sensor_manager = SensorManager(self.config)
            await self.sensor_manager.initialize()
            
            self.led_controller = LEDController(self.config)
            await self.led_controller.initialize()
            
            # Инициализация AI
            self.wake_word_detector = WakeWordDetector(self.config)
            await self.wake_word_detector.initialize()
            
            self.speech_to_text = SpeechToText(self.config)
            await self.speech_to_text.initialize()
            
            self.text_to_speech = TextToSpeech(self.config)
            await self.text_to_speech.initialize()
            
            self.llm_service = LLMService(self.config)
            await self.llm_service.initialize()
            
            self.vision_service = VisionService(self.config)
            await self.vision_service.initialize()
            
            # Инициализация системы эмоций
            self.emotion_engine = EmotionEngine(self.config)
            await self.emotion_engine.initialize()
            
            # Инициализация сервисов
            self.smart_home_service = SmartHomeService(self.config)
            await self.smart_home_service.initialize()
            
            self.internet_service = InternetService(self.config)
            await self.internet_service.initialize()
            
            self.media_service = MediaService(self.config)
            await self.media_service.initialize()
            
            self.logger.info("Робот Eva успешно инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Запуск основного цикла робота"""
        self.is_running = True
        self.logger.info("Запуск робота Eva...")
        
            # Установка начальной эмоции
        await self.emotion_engine.set_emotion("neutral")
        await self.display_manager.show_animation("neutral")
        await self.led_controller.set_status("ready")
        
        # Запуск мониторинга датчика присутствия
        asyncio.create_task(self._monitor_presence())
        
        # Запуск основного цикла
        await self._main_loop()
    
    async def _monitor_presence(self):
        """Мониторинг датчика присутствия"""
        while self.is_running:
            try:
                presence_data = await self.sensor_manager.get_presence_data()
                
                if presence_data.get("human_detected"):
                    self.logger.info("Обнаружен человек")
                    await self.led_controller.set_status("active")
                    await self.emotion_engine.set_emotion("happy")
                    await self.display_manager.show_animation("happy")
                    
                    # Приветствие
                    if not self.is_listening:
                        await self._greet_user()
                        await self._start_conversation()
                
                elif presence_data.get("sleep_detected"):
                    self.logger.info("Обнаружен сон")
                    await self.emotion_engine.set_emotion("sleepy")
                    await self.display_manager.show_animation("sleepy")
                    await self.led_controller.set_status("sleep")
                
                elif presence_data.get("heart_rate"):
                    self.logger.debug(f"Сердцебиение: {presence_data['heart_rate']} bpm")
                
                await asyncio.sleep(0.5)  # Проверка каждые 0.5 секунды
                
            except Exception as e:
                self.logger.error(f"Ошибка в мониторинге присутствия: {e}")
                await asyncio.sleep(1)
    
    async def _main_loop(self):
        """Основной цикл работы робота"""
        while self.is_running:
            try:
                # Ожидание wake word
                if await self.wake_word_detector.detect():
                    self.logger.info("Wake word обнаружен!")
                    await self.led_controller.set_status("listening")
                    await self.emotion_engine.set_emotion("listening")
                    await self.display_manager.show_animation("listening")
                    
                    # Слушаем команду
                    await self._process_command()
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _greet_user(self):
        """Приветствие пользователя"""
        greeting = await self.llm_service.generate_greeting()
        await self.text_to_speech.speak(greeting)
        await self.emotion_engine.set_emotion("happy")
    
    async def _start_conversation(self):
        """Начало разговора с пользователем"""
        self.is_listening = True
        
        # Описание того, что видит камера
        if self.camera_manager.is_available():
            frame = await self.camera_manager.capture_frame()
            if frame is not None:
                vision_description = await self.vision_service.describe_scene(frame)
                if vision_description:
                    response = await self.llm_service.generate_response(
                        f"Я вижу: {vision_description}. Что бы ты хотел обсудить?"
                    )
                    await self.text_to_speech.generate_and_play(response, self.audio_manager)
    
    async def _process_command(self):
        """Обработка команды пользователя"""
        try:
            # Запись аудио
            audio_data = await self.audio_manager.record_audio(
                duration=self.config.get("audio.record_duration", 5)
            )
            
            # Распознавание речи
            text = await self.speech_to_text.transcribe(audio_data)
            if not text:
                await self.text_to_speech.speak("Извините, я не расслышал")
                return
            
            self.logger.info(f"Распознано: {text}")
            
            # Обработка команды через LLM
            command_response = await self.llm_service.process_command(text)
            
            # Выполнение действий если нужно
            await self._execute_actions(command_response)
            
            # Генерация ответа
            answer = await self.llm_service.generate_response(text, context=command_response)
            
            # Обновление анимации на дисплее
            emotion = await self.llm_service.detect_emotion(answer)
            await self.emotion_engine.set_emotion(emotion.value if hasattr(emotion, 'value') else emotion)
            await self.display_manager.show_animation(emotion.value if hasattr(emotion, 'value') else emotion)
            
            # Воспроизведение ответа
            if answer:
                await self.text_to_speech.generate_and_play(answer, self.audio_manager)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды: {e}", exc_info=True)
            await self.text_to_speech.speak("Произошла ошибка при обработке команды")
        finally:
            self.is_listening = False
            await self.led_controller.set_status("ready")
    
    async def _execute_actions(self, response: dict):
        """Выполнение действий на основе ответа LLM"""
        actions = response.get("actions", [])
        
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "smart_home":
                await self.smart_home_service.execute(action.get("command"))
            
            elif action_type == "search":
                results = await self.internet_service.search(action.get("query"))
                response["search_results"] = results
            
            elif action_type == "play_music":
                await self.media_service.play_music(action.get("query"))
            
            elif action_type == "play_video":
                await self.media_service.play_video(action.get("url"))
            
            elif action_type == "servo_move":
                await self.servo_controller.move(
                    action.get("servo"),
                    action.get("angle")
                )
    
    async def stop(self):
        """Остановка робота"""
        self.logger.info("Остановка робота Eva...")
        self.is_running = False
        
        # Остановка всех компонентов
        if self.servo_controller:
            await self.servo_controller.cleanup()
        if self.display_manager:
            await self.display_manager.cleanup()
        if self.audio_manager:
            await self.audio_manager.cleanup()
        if self.camera_manager:
            await self.camera_manager.cleanup()
        if self.sensor_manager:
            await self.sensor_manager.cleanup()
        if self.led_controller:
            await self.led_controller.cleanup()
        
        self.logger.info("Робот Eva остановлен")

