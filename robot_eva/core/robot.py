"""
Главный класс робота Eva
"""
import asyncio
import logging
import random
import time
import os
import sys
from typing import Optional
from .config import Config
from ..hardware.servos import create_servo_controller
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
from ..behaviors.motion import MotionBehavior
from ..behaviors.face_tracking import FaceTrackingBehavior
from ..behaviors.heart_gesture import HeartGestureBehavior
from ..behaviors.gun_gesture import GunGestureBehavior
from ..services.smart_home import SmartHomeService
from ..services.internet import InternetService
from ..services.media import MediaService
from ..utils.robot_actions import extract_robot_actions


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
        self.motion_behavior = None
        self.face_tracking_behavior = None
        self.heart_gesture_behavior = None
        self.gun_gesture_behavior = None
        self.smart_home_service = None
        self.internet_service = None
        self.media_service = None
        
        self.is_running = False
        self.is_listening = False

        # Idle chat (Eva initiates conversation)
        self._idle_chat_task: Optional[asyncio.Task] = None
        self._last_interaction_ts: float = time.time()

        # Watchdog / health
        self._watchdog_task: Optional[asyncio.Task] = None
        self._heartbeat_ts: float = time.time()
        self._listening_started_ts: Optional[float] = None
        self._restart_in_progress: bool = False
        self._speaking_flag: bool = False

    async def _set_speaking(self, is_speaking: bool) -> None:
        self._speaking_flag = bool(is_speaking)
        if self.face_tracking_behavior:
            try:
                self.face_tracking_behavior.set_paused(self._speaking_flag)
            except Exception:
                pass

    async def _tts_play(self, text: str) -> None:
        """
        Synthesize TTS and play it.

        IMPORTANT: mouth/gesture "speaking" overlay should match *actual speaker audio*,
        so we only enable speaking state during playback, not during TTS generation.
        """
        if not self.text_to_speech:
            return
        text = (text or "").strip()
        if not text:
            return

        # If we cannot play audio, fall back to synthesis only (no mouth animation expected).
        if not self.audio_manager:
            try:
                await self.text_to_speech.speak(text)
            except Exception:
                pass
            return

        # Generate audio first (network), then enable speaking only while playing.
        audio = await self.text_to_speech.speak(text)
        if not audio:
            return

        if self.motion_behavior:
            await self.motion_behavior.notify_speaking(True)
        await self._set_speaking(True)
        if self.display_manager:
            await self.display_manager.set_speaking(True)
        if self.led_controller:
            await self.led_controller.set_status("speaking")
        try:
            await self.audio_manager.play_audio(audio)
        finally:
            if self.motion_behavior:
                await self.motion_behavior.notify_speaking(False)
            await self._set_speaking(False)
            if self.display_manager:
                await self.display_manager.set_speaking(False)

    def _gestures_should_run(self) -> bool:
        if not bool(self.config.get("behavior.gestures.enabled", True)):
            return False
        if not bool(self.is_running) or bool(self.is_listening) or bool(getattr(self, "_speaking_flag", False)):
            return False
        try:
            window = float(self.config.get("behavior.gestures.active_window_seconds", 0))
        except Exception:
            window = 0.0
        # window <= 0 => always
        if window <= 0:
            return True
        return (time.time() - float(self._last_interaction_ts or 0.0)) <= window

    def _heartbeat(self):
        self._heartbeat_ts = time.time()

    @staticmethod
    def _short(text: str, limit: int = 160) -> str:
        try:
            s = (text or "").strip().replace("\n", " ")
        except Exception:
            return ""
        if len(s) <= limit:
            return s
        return s[: max(0, limit - 1)] + "…"
    
    async def initialize(self):
        """Инициализация всех компонентов робота"""
        self.logger.info("Инициализация робота Eva...")
        
        try:
            # Инициализация железа (с обработкой ошибок для каждого компонента)
            self.servo_controller = create_servo_controller(self.config)
            try:
                await self.servo_controller.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать сервоприводы: {e}")

            # Behavior layer (motions/gestures) - optional, uses servo controller
            self.motion_behavior = MotionBehavior(self.config, self.servo_controller)
            try:
                await self.motion_behavior.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать MotionBehavior: {e}")
                self.motion_behavior = None
            
            self.display_manager = DisplayManager(self.config)
            try:
                await self.display_manager.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать дисплеи: {e}")
            
            self.audio_manager = AudioManager(self.config)
            try:
                await self.audio_manager.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать аудио: {e}")
            
            self.camera_manager = CameraManager(self.config)
            try:
                await self.camera_manager.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать камеру: {e}")

            # Face tracking behavior (camera -> head follow)
            self.face_tracking_behavior = FaceTrackingBehavior(self.config, self.camera_manager, self.servo_controller)
            try:
                await self.face_tracking_behavior.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать FaceTrackingBehavior: {e}")
                self.face_tracking_behavior = None
            
            self.sensor_manager = SensorManager(self.config)
            try:
                await self.sensor_manager.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать сенсоры: {e}")
            
            self.led_controller = LEDController(self.config)
            try:
                await self.led_controller.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать LED: {e}")
            
            # Инициализация AI (с обработкой ошибок)
            self.wake_word_detector = WakeWordDetector(self.config)
            try:
                await self.wake_word_detector.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать wake word детектор: {e}")
                self.wake_word_detector = None
            
            self.speech_to_text = SpeechToText(self.config)
            try:
                await self.speech_to_text.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать распознавание речи: {e}")
                self.speech_to_text = None
            
            self.text_to_speech = TextToSpeech(self.config)
            try:
                await self.text_to_speech.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать синтез речи: {e}")
                self.text_to_speech = None
            
            self.llm_service = LLMService(self.config)
            try:
                await self.llm_service.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать LLM сервис: {e}")
                self.llm_service = None
            
            self.vision_service = VisionService(self.config)
            try:
                await self.vision_service.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать компьютерное зрение: {e}")
                self.vision_service = None
            
            # Инициализация системы эмоций (обязательно)
            self.emotion_engine = EmotionEngine(self.config)
            try:
                await self.emotion_engine.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать систему эмоций: {e}")
                # Создаем заглушку, чтобы не было ошибок
                self.emotion_engine = None

            # Gesture: heart -> love animation (vision-based)
            async def _on_heart():
                if self.emotion_engine:
                    await self.emotion_engine.set_emotion("love")
                if self.display_manager:
                    await self.display_manager.show_animation("love")
                if self.motion_behavior:
                    await self.motion_behavior.notify_emotion("love")
                # Optional physical gesture
                try:
                    if self.servo_controller and hasattr(self.servo_controller, "wave_arms"):
                        await self.servo_controller.wave_arms(times=1)
                except Exception:
                    pass

                # Say a short phrase
                phrase = str(self.config.get("behavior.gestures.heart.tts_phrase", "Я тоже тебя люблю!") or "").strip()
                if phrase:
                    await self._tts_play(phrase)

                # Return animation/emotion back to neutral after a short time
                try:
                    duration_s = float(self.config.get("behavior.gestures.heart.display_duration_seconds", 6.0))
                except Exception:
                    duration_s = 6.0
                duration_s = max(1.0, min(60.0, duration_s))

                async def _return_to_neutral_later():
                    try:
                        await asyncio.sleep(duration_s)
                        # Don't override active interaction states
                        if not self.is_running:
                            return
                        if self.is_listening or getattr(self, "_speaking_flag", False):
                            return
                        # Only revert if we're still in love
                        try:
                            cur = getattr(self.emotion_engine, "current_emotion", None) if self.emotion_engine else None
                            cur_val = getattr(cur, "value", str(cur)) if cur is not None else ""
                        except Exception:
                            cur_val = ""
                        if str(cur_val).lower() != "love":
                            return
                        if self.emotion_engine:
                            await self.emotion_engine.set_emotion("neutral")
                        if self.display_manager:
                            await self.display_manager.show_animation("neutral")
                        if self.motion_behavior:
                            await self.motion_behavior.notify_emotion("neutral")
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        return

                asyncio.create_task(_return_to_neutral_later(), name="heart-return-neutral")

            self.heart_gesture_behavior = HeartGestureBehavior(
                self.config,
                self.camera_manager,
                self.vision_service,
                should_run=self._gestures_should_run,
                on_heart=_on_heart,
            )
            try:
                await self.heart_gesture_behavior.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать HeartGestureBehavior: {e}")
                self.heart_gesture_behavior = None

            # Gesture: finger gun -> raise right arm + say "пиф пфф"
            async def _on_gun():
                # Show a playful animation
                if self.emotion_engine:
                    await self.emotion_engine.set_emotion("play")
                if self.display_manager:
                    await self.display_manager.show_animation("play")
                if self.motion_behavior:
                    await self.motion_behavior.notify_emotion("play")

                # Raise right arm to a configured angle (pistol pose)
                try:
                    angle = float(self.config.get("behavior.gestures.gun.right_arm_angle", 40.0))
                except Exception:
                    angle = 40.0
                try:
                    duration_s = float(self.config.get("behavior.gestures.gun.right_arm_duration_seconds", 0.9))
                except Exception:
                    duration_s = 0.9
                angle = max(0.0, min(180.0, angle))
                duration_s = max(0.2, min(3.0, duration_s))

                try:
                    if self.servo_controller:
                        right_arm = getattr(self.servo_controller, "SERVO_RIGHT_ARM", 4)
                        if hasattr(self.servo_controller, "move_smooth"):
                            await self.servo_controller.move_smooth(right_arm, angle, steps=8, delay=max(0.02, duration_s / 8))
                        else:
                            await self.servo_controller.move(right_arm, angle)
                except Exception:
                    pass

                # Say pew-pew
                phrase = str(self.config.get("behavior.gestures.gun.tts_phrase", "пиф пфф") or "").strip()
                if phrase:
                    await self._tts_play(phrase)

                # Return to neutral after a short time
                try:
                    keep_s = float(self.config.get("behavior.gestures.gun.display_duration_seconds", 4.0))
                except Exception:
                    keep_s = 4.0
                keep_s = max(1.0, min(60.0, keep_s))

                async def _return_to_neutral_later():
                    try:
                        await asyncio.sleep(keep_s)
                        if not self.is_running:
                            return
                        if self.is_listening or getattr(self, "_speaking_flag", False):
                            return
                        # Don't override if emotion has changed
                        try:
                            cur = getattr(self.emotion_engine, "current_emotion", None) if self.emotion_engine else None
                            cur_val = getattr(cur, "value", str(cur)) if cur is not None else ""
                        except Exception:
                            cur_val = ""
                        if str(cur_val).lower() != "play":
                            return
                        if self.emotion_engine:
                            await self.emotion_engine.set_emotion("neutral")
                        if self.display_manager:
                            await self.display_manager.show_animation("neutral")
                        if self.motion_behavior:
                            await self.motion_behavior.notify_emotion("neutral")
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        return

                asyncio.create_task(_return_to_neutral_later(), name="gun-return-neutral")

            self.gun_gesture_behavior = GunGestureBehavior(
                self.config,
                self.camera_manager,
                self.vision_service,
                should_run=self._gestures_should_run,
                on_gun=_on_gun,
            )
            try:
                await self.gun_gesture_behavior.initialize()
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать GunGestureBehavior: {e}")
                self.gun_gesture_behavior = None
            
            # Инициализация сервисов
            self.smart_home_service = SmartHomeService(self.config)
            await self.smart_home_service.initialize()
            
            self.internet_service = InternetService(self.config)
            await self.internet_service.initialize()
            
            self.media_service = MediaService(self.config)
            await self.media_service.initialize()
            
            self.logger.info("Робот Eva успешно инициализирован (некоторые компоненты могут быть недоступны)")
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка при инициализации: {e}", exc_info=True)
            # Не прерываем выполнение, продолжаем с доступными компонентами
            self.logger.warning("Продолжение работы с ограниченным функционалом")
    
    async def start(self):
        """Запуск основного цикла робота"""
        self.is_running = True
        self.logger.info("Запуск робота Eva...")
        
            # Установка начальной эмоции
        if self.emotion_engine:
            await self.emotion_engine.set_emotion("neutral")
        if self.display_manager:
            await self.display_manager.show_animation("neutral")
        if self.led_controller:
            await self.led_controller.set_status("ready")
        if self.motion_behavior:
            await self.motion_behavior.start()
        if self.face_tracking_behavior:
            try:
                await self.face_tracking_behavior.start()
            except Exception:
                pass
        if self.heart_gesture_behavior:
            try:
                await self.heart_gesture_behavior.start()
            except Exception:
                pass
        if self.gun_gesture_behavior:
            try:
                await self.gun_gesture_behavior.start()
            except Exception:
                pass

        # Приветствие при запуске (рандомная фраза)
        await self._startup_greeting()
        
        # Запуск мониторинга датчика присутствия
        asyncio.create_task(self._monitor_presence())

        # Автодиалог (раз в случайный интервал)
        if self.config.get("behavior.idle_chat.enabled", False):
            self._idle_chat_task = asyncio.create_task(self._idle_chat_loop(), name="idle-chat")

        # Watchdog (auto-restart on hangs)
        if self.config.get("behavior.watchdog.enabled", True):
            self._watchdog_task = asyncio.create_task(self._watchdog_loop(), name="watchdog")
        
        # Запуск основного цикла
        await self._main_loop()

    async def _startup_greeting(self):
        """Приветствие при запуске (один раз)"""
        if not self.config.get("behavior.startup_greeting.enabled", True):
            return
        if not self.text_to_speech:
            return

        phrases = self.config.get("behavior.startup_greeting.phrases", None)
        if not phrases or not isinstance(phrases, list):
            phrases = [
                "Привет! Я Ева.",
                "Привет, я Ева. Я на связи.",
                "Хэй! Ева здесь.",
                "Привет! Готова помочь.",
                "Привет! Чем займёмся?",
            ]
        phrases = [p for p in phrases if isinstance(p, str) and p.strip()]
        if not phrases:
            return

        text = random.choice(phrases).strip()
        self.logger.info(f"Startup greeting: {text}")

        # Optional: look at the camera and say what we see.
        describe_camera = bool(self.config.get("behavior.startup_greeting.describe_camera.enabled", False))
        if describe_camera and self.camera_manager and self.camera_manager.is_available() and self.vision_service:
            lang = (self.config.get("ai.language.default", "") or "").strip().lower() or "ru"
            timeout_s = float(self.config.get("behavior.startup_greeting.describe_camera.timeout_seconds", 10.0))
            timeout_s = max(2.0, min(timeout_s, 30.0))

            # Short prompt for startup phrase.
            if lang == "en":
                vision_prompt = "Briefly describe what you see in this image in ONE short sentence."
                prefix = "I can see:"
            elif lang == "th":
                vision_prompt = "บอกสั้น ๆ ว่าคุณเห็นอะไรในภาพนี้ (1 ประโยคสั้น ๆ)"
                prefix = "ฉันเห็น:"
            else:
                vision_prompt = "Коротко опиши, что ты видишь на изображении, ОДНИМ коротким предложением."
                prefix = "Я вижу:"

            try:
                frame = await asyncio.wait_for(self.camera_manager.capture_frame(), timeout=timeout_s)
                vision_desc = await asyncio.wait_for(
                    self.vision_service.describe_scene(frame, prompt=vision_prompt, language=lang, max_tokens=80),
                    timeout=timeout_s,
                )
                vision_desc = (vision_desc or "").strip()
                if vision_desc:
                    # Merge into one TTS call so it sounds natural.
                    text = f"{text} {prefix} {vision_desc}"
                    self.logger.info(f"Startup camera description: {vision_desc}")
            except Exception as e:
                self.logger.warning(f"Startup camera description failed: {e}")

        # Опционально: поставить эмоцию/анимацию на старте
        startup_emotion = (self.config.get("behavior.startup_greeting.emotion", "") or "").strip().lower()
        if startup_emotion:
            if self.emotion_engine:
                await self.emotion_engine.set_emotion(startup_emotion)
            if self.display_manager:
                await self.display_manager.show_animation(startup_emotion)
            if self.motion_behavior:
                await self.motion_behavior.notify_emotion(startup_emotion)

        try:
            await self._tts_play(text)
            self.logger.info("Startup greeting: played")
        except Exception as e:
            # Не роняем запуск из-за проблем с аудио.
            self.logger.warning(f"Startup greeting failed (audio issue?): {e}")
        finally:
            if self.led_controller:
                await self.led_controller.set_status("ready")
    
    async def _monitor_presence(self):
        """Мониторинг датчика присутствия"""
        while self.is_running:
            try:
                if not self.sensor_manager:
                    await asyncio.sleep(1)
                    continue
                
                presence_data = await self.sensor_manager.get_presence_data()
                
                if presence_data.get("human_detected"):
                    self.logger.info("Обнаружен человек")
                    if self.led_controller:
                        await self.led_controller.set_status("active")
                    if self.emotion_engine:
                        await self.emotion_engine.set_emotion("happy")
                    if self.display_manager:
                        await self.display_manager.show_animation("happy")
                    if self.motion_behavior:
                        await self.motion_behavior.notify_emotion("happy")
                    
                    # Приветствие
                    if not self.is_listening:
                        await self._greet_user()
                        await self._start_conversation()
                
                elif presence_data.get("sleep_detected"):
                    self.logger.info("Обнаружен сон")
                    if self.emotion_engine:
                        await self.emotion_engine.set_emotion("sleep")
                    if self.display_manager:
                        await self.display_manager.show_animation("sleep")
                    if self.led_controller:
                        await self.led_controller.set_status("sleep")
                    if self.motion_behavior:
                        await self.motion_behavior.notify_emotion("sleep")
                
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
                self._heartbeat()
                # Если уже слушаем/обрабатываем — не запускаем wake word детект (иначе будут гонки по аудио)
                if self.is_listening:
                    await asyncio.sleep(0.1)
                    continue

                # Ожидание wake word (OpenWakeWord)
                if self.wake_word_detector:
                    if await self.wake_word_detector.detect():
                        self.logger.info("Wake word обнаружен!")
                        if self.led_controller:
                            await self.led_controller.set_status("listening")
                        if self.emotion_engine:
                            await self.emotion_engine.set_emotion("listening")
                        if self.display_manager:
                            await self.display_manager.show_animation("listening")
                        if self.motion_behavior:
                            await self.motion_behavior.notify_emotion("listening")
                        
                        # Слушаем команду
                        await self._process_command()
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _watchdog_loop(self):
        """Restart process if robot is stuck (e.g. listening too long / no heartbeat)."""
        try:
            check_interval = float(self.config.get("behavior.watchdog.check_interval_seconds", 2.0))
            stuck_listening_s = float(self.config.get("behavior.watchdog.stuck_listening_seconds", 25.0))
            no_heartbeat_s = float(self.config.get("behavior.watchdog.no_heartbeat_seconds", 60.0))
            restart_delay_s = float(self.config.get("behavior.watchdog.restart_delay_seconds", 1.5))

            check_interval = max(0.5, check_interval)
            stuck_listening_s = max(5.0, stuck_listening_s)
            no_heartbeat_s = max(10.0, no_heartbeat_s)
            restart_delay_s = max(0.0, restart_delay_s)

            while self.is_running:
                await asyncio.sleep(check_interval)
                if not self.is_running:
                    break
                if self._restart_in_progress:
                    continue

                now = time.time()

                # If event loop is alive but no heartbeat updates for too long -> restart.
                if (now - (self._heartbeat_ts or now)) > no_heartbeat_s:
                    await self._restart_process(f"no heartbeat for {now - self._heartbeat_ts:.1f}s")
                    return

                # Stuck in listening/command handling too long -> restart.
                if self.is_listening and self._listening_started_ts:
                    if (now - self._listening_started_ts) > stuck_listening_s:
                        await self._restart_process(f"stuck listening for {now - self._listening_started_ts:.1f}s")
                        return

        except asyncio.CancelledError:
            return
        except Exception as e:
            self.logger.warning(f"Watchdog error: {e}")

    async def _restart_process(self, reason: str):
        """Best-effort self-restart (exec)."""
        if self._restart_in_progress:
            return
        self._restart_in_progress = True
        self.logger.error(f"WATCHDOG: restarting process ({reason})")

        try:
            await asyncio.sleep(float(self.config.get("behavior.watchdog.restart_delay_seconds", 1.5)))
        except Exception:
            pass

        # Try graceful stop, but do not hang on it.
        try:
            await asyncio.wait_for(self.stop(), timeout=10)
        except Exception:
            pass

        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            self.logger.error(f"WATCHDOG: execv failed: {e}")
            os._exit(2)

    async def _idle_chat_loop(self):
        """Ева сама инициирует разговор: говорит -> слушает -> отвечает."""
        try:
            interval = self.config.get("behavior.idle_chat.interval_seconds", [180, 420])
            try:
                lo = float(interval[0])
                hi = float(interval[1])
            except Exception:
                lo, hi = 180.0, 420.0
            lo = max(10.0, lo)
            hi = max(lo + 1.0, hi)

            prompts = self.config.get("behavior.idle_chat.prompts", None)
            if not prompts or not isinstance(prompts, list):
                prompts = [
                    "Скучно. Поговорим?",
                    "Как дела? Что нового?",
                    "Хочешь, расскажу что-нибудь интересное?",
                ]
            prompts = [p.strip() for p in prompts if isinstance(p, str) and p.strip()]

            require_presence = bool(self.config.get("behavior.idle_chat.require_human_detected", False))
            listen_duration = float(self.config.get("behavior.idle_chat.listen_duration", 5))

            while self.is_running:
                await asyncio.sleep(random.uniform(lo, hi))

                if not self.is_running:
                    break
                if self.is_listening:
                    continue

                # If presence is required and sensor exists -> check.
                if require_presence and self.sensor_manager:
                    try:
                        presence = await self.sensor_manager.get_presence_data()
                        if not presence.get("human_detected"):
                            continue
                    except Exception:
                        continue

                # If we had recent interaction, postpone.
                if (time.time() - self._last_interaction_ts) < lo:
                    continue

                if not prompts:
                    continue

                prompt = random.choice(prompts)
                self.logger.info(f"Idle chat prompt: {prompt}")
                self._heartbeat()

                # Show friendly emotion
                if self.emotion_engine:
                    await self.emotion_engine.set_emotion("happy")
                if self.display_manager:
                    await self.display_manager.show_animation("happy")
                if self.motion_behavior:
                    await self.motion_behavior.notify_emotion("happy")

                # Small physical gesture to get attention
                try:
                    if self.servo_controller and hasattr(self.servo_controller, "wave_arms"):
                        await self.servo_controller.wave_arms(times=1)
                    elif self.servo_controller and hasattr(self.servo_controller, "nod_head"):
                        await self.servo_controller.nod_head(times=1)
                except Exception:
                    pass

                # Speak prompt
                try:
                    if self.text_to_speech:
                        await self._tts_play(prompt)
                except Exception as e:
                    self.logger.warning(f"Idle chat speak failed: {e}")
                    continue
                finally:
                    pass

                # Now listen and respond (without wake word)
                self._last_interaction_ts = time.time()
                await self._process_command(record_duration=listen_duration)
                self._last_interaction_ts = time.time()
                self._heartbeat()

        except asyncio.CancelledError:
            return
        except Exception as e:
            self.logger.warning(f"Idle chat loop error: {e}")
    
    async def _greet_user(self):
        """Приветствие пользователя"""
        if not self.llm_service:
            return
        greeting = await self.llm_service.generate_greeting()
        if greeting and self.text_to_speech:
            # Note: speak() only synthesizes; generate_and_play() plays through AudioManager if available.
            try:
                await self._tts_play(greeting)
            finally:
                pass
        if self.emotion_engine:
            await self.emotion_engine.set_emotion("happy")
        if self.motion_behavior:
            await self.motion_behavior.notify_emotion("happy")
    
    async def _start_conversation(self):
        """Начало разговора с пользователем"""
        self.is_listening = True
        
        # Описание того, что видит камера
        if self.camera_manager and self.camera_manager.is_available() and self.vision_service and self.llm_service:
            frame = await self.camera_manager.capture_frame()
            if frame is not None:
                vision_description = await self.vision_service.describe_scene(frame)
                if vision_description:
                    response = await self.llm_service.generate_response(
                        f"Я вижу: {vision_description}. Что бы ты хотел обсудить?"
                    )
                    if self.text_to_speech:
                        await self._tts_play(response)
    
    async def _process_command(self, record_duration: Optional[float] = None):
        """Обработка команды пользователя"""
        return await self._process_command_impl(record_duration=record_duration, allow_dialogue=True, silent_on_no_speech=False)

    async def _process_command_impl(
        self,
        *,
        record_duration: Optional[float],
        allow_dialogue: bool,
        silent_on_no_speech: bool,
    ) -> bool:
        """
        Returns True if we recognized non-empty user speech (STT), else False.
        """
        try:
            self.is_listening = True
            self._last_interaction_ts = time.time()
            # IMPORTANT for watchdog:
            # `_listening_started_ts` should represent *microphone recording* time only.
            # LLM + TTS can legitimately take > stuck_listening_seconds.
            self._listening_started_ts = None
            self._heartbeat()

            # Stop wake-word recorder before opening PyAudio input stream.
            # PvRecorder (OpenWakeWord) and PyAudio can conflict on the same mic device -> Errno -9985.
            if self.wake_word_detector:
                try:
                    await self.wake_word_detector.stop_listening()
                except Exception:
                    pass

            # Listening state while recording audio
            if self.led_controller:
                await self.led_controller.set_status("listening")
            if self.emotion_engine:
                await self.emotion_engine.set_emotion("listening")
            if self.display_manager:
                await self.display_manager.show_animation("listening")
            if self.motion_behavior:
                await self.motion_behavior.notify_emotion("listening")

            # Проверка доступности компонентов
            if not self.audio_manager:
                self.logger.warning("Аудио менеджер недоступен")
                return

            dur = float(record_duration) if record_duration is not None else float(self.config.get("audio.record_duration", 5))
            self.logger.info(f"Listening: recording audio (duration={dur:.1f}s)")
            
            # Запись аудио
            self._listening_started_ts = time.time()
            audio_data = await self.audio_manager.record_audio(
                duration=dur
            )
            # Recording finished -> clear timer so watchdog doesn't restart during LLM/TTS.
            self._listening_started_ts = None
            self._heartbeat()
            try:
                self.logger.info(f"Listening: recorded audio bytes={len(audio_data)}")
            except Exception:
                pass
            
            # Распознавание речи
            if not self.speech_to_text:
                self.logger.warning("Сервис распознавания речи недоступен")
                return False
            
            text = await self.speech_to_text.transcribe(audio_data)
            if not text:
                if not silent_on_no_speech:
                    if self.text_to_speech:
                        await self._tts_play("Извините, я не расслышал")
                return False

            self._last_interaction_ts = time.time()
            self._heartbeat()
            
            self.logger.info(f"Heard (STT): {self._short(text)}")

            # Thinking state while we call LLM / actions
            if self.led_controller:
                await self.led_controller.set_status("thinking")
            if self.emotion_engine:
                await self.emotion_engine.set_emotion("thinking")
            if self.display_manager:
                await self.display_manager.show_animation("thinking")
            if self.motion_behavior:
                await self.motion_behavior.notify_emotion("thinking")

            self.logger.info("LLM: processing command/actions…")
            
            # Обработка команды через LLM
            if not self.llm_service:
                self.logger.warning("LLM сервис недоступен")
                return
            
            command_response = await self.llm_service.process_command(text)
            try:
                actions = (command_response or {}).get("actions") or []
                self.logger.info(f"LLM: actions parsed count={len(actions)}")
            except Exception:
                pass
            
            # Выполнение действий если нужно
            await self._execute_actions(command_response)
            
            # Генерация ответа
            self.logger.info("LLM: generating final answer…")
            raw_answer = await self.llm_service.generate_response(text, context=command_response)
            answer, robot_actions = extract_robot_actions(raw_answer)
            if answer:
                self.logger.info(f"LLM answer: {self._short(answer)}")

            # Apply robot actions provided by LLM (emotions/animations/gestures)
            try:
                await self._apply_robot_actions(robot_actions)
            except Exception:
                pass
            
            # Обновление анимации на дисплее
            has_explicit = any(
                isinstance(a, dict) and str(a.get("type", "")).lower() in ("emotion", "animation")
                for a in (robot_actions or [])
            )
            if not has_explicit:
                emotion = await self.llm_service.detect_emotion(answer)
                emotion_str = emotion.value if hasattr(emotion, 'value') else emotion
                if self.emotion_engine:
                    await self.emotion_engine.set_emotion(emotion_str)
                if self.display_manager:
                    await self.display_manager.show_animation(emotion_str)
                if self.motion_behavior:
                    await self.motion_behavior.notify_emotion(emotion_str)
            
            # Воспроизведение ответа
            if answer and self.text_to_speech:
                try:
                    self.logger.info("TTS: playing answer…")
                    await self._tts_play(answer)
                    self.logger.info("TTS: done")
                finally:
                    pass

            # Dialogue mode: after Eva speaks, listen for a reply and continue without wake word.
            if allow_dialogue and bool(self.config.get("behavior.dialogue.enabled", True)):
                try:
                    max_turns = int(self.config.get("behavior.dialogue.max_turns", 3))
                except Exception:
                    max_turns = 3
                max_turns = max(0, min(10, max_turns))
                try:
                    listen_dur = float(self.config.get("behavior.dialogue.listen_duration", 5))
                except Exception:
                    listen_dur = 5.0
                listen_dur = max(1.0, min(30.0, listen_dur))
                silent = bool(self.config.get("behavior.dialogue.silent_on_no_speech", True))

                for _ in range(max_turns):
                    # Wait for a user reply
                    self.logger.info("Dialogue: listening for reply…")
                    ok = await self._process_command_impl(
                        record_duration=listen_dur,
                        allow_dialogue=False,
                        silent_on_no_speech=silent,
                    )
                    if not ok:
                        break
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды: {e}", exc_info=True)
            if self.text_to_speech:
                await self._tts_play("Произошла ошибка при обработке команды")
            return False
        finally:
            self.is_listening = False
            self._listening_started_ts = None
            if self.led_controller:
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

    async def _apply_robot_actions(self, actions):
        """Apply robot_actions parsed from the LLM answer text."""
        if not actions or not isinstance(actions, list):
            return

        for a in actions:
            if not isinstance(a, dict):
                continue
            t = str(a.get("type", "") or "").strip().lower()
            if not t:
                continue

            if t == "emotion":
                val = str(a.get("value", "") or "").strip().lower()
                if not val:
                    continue
                if self.emotion_engine:
                    await self.emotion_engine.set_emotion(val)
                if self.display_manager:
                    await self.display_manager.show_animation(val)
                if self.motion_behavior:
                    await self.motion_behavior.notify_emotion(val)
                continue

            if t == "animation":
                name = str(a.get("name", "") or "").strip().lower()
                if name and self.display_manager:
                    await self.display_manager.show_animation(name)
                continue

            if t == "gesture":
                name = str(a.get("name", "") or "").strip().lower()
                try:
                    times = int(a.get("times", 1))
                except Exception:
                    times = 1
                times = max(1, min(5, times))
                if not self.servo_controller:
                    continue
                try:
                    if name == "wave_arms" and hasattr(self.servo_controller, "wave_arms"):
                        await self.servo_controller.wave_arms(times=times)
                    elif name == "nod_head" and hasattr(self.servo_controller, "nod_head"):
                        await self.servo_controller.nod_head(times=times)
                    elif name == "shake_head" and hasattr(self.servo_controller, "shake_head"):
                        await self.servo_controller.shake_head(times=times)
                except Exception:
                    pass
                continue
    
    async def stop(self):
        """Остановка робота"""
        self.logger.info("Остановка робота Eva...")
        self.is_running = False

        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._watchdog_task = None
        
        # Остановка всех компонентов
        if self._idle_chat_task:
            self._idle_chat_task.cancel()
            try:
                await self._idle_chat_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._idle_chat_task = None
        if self.gun_gesture_behavior:
            try:
                await self.gun_gesture_behavior.stop()
            except Exception:
                pass
            self.gun_gesture_behavior = None
        if self.heart_gesture_behavior:
            try:
                await self.heart_gesture_behavior.stop()
            except Exception:
                pass
            self.heart_gesture_behavior = None
        if self.face_tracking_behavior:
            try:
                await self.face_tracking_behavior.stop()
            except Exception:
                pass
            self.face_tracking_behavior = None
        if self.motion_behavior:
            try:
                await self.motion_behavior.stop()
            except Exception:
                pass
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

