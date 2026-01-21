"""
Контейнер сознания робота - основной модуль для самообучения и эволюции
"""
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from .emotions import EmotionEngine as AdvancedEmotionEngine
from .sandbox import CodeSandbox
from .reflection import ReflectionEngine
from .learning import LearningEngine
from .code_self_analysis import CodeSelfAnalysis
from .social_learning import SocialLearningSystem
from .collective_intelligence import CollectiveIntelligence
from .meta_emotions import MetaEmotionsSystem
from .creativity import CreativitySystem
from .context_memory import ContextMemorySystem


class ConsciousnessContainer:
    """
    Контейнер сознания робота
    
    Объединяет:
    - Систему эмоций (создание и эволюция)
    - Безопасную песочницу (выполнение кода)
    - Рефлексию (самоанализ)
    - Обучение (эволюция поведения)
    """
    
    def __init__(self, config, robot_instance: Optional[Any] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.robot = robot_instance
        
        # Инициализация компонентов
        self.emotion_engine = AdvancedEmotionEngine(config)
        self.code_sandbox = CodeSandbox(config)
        self.reflection_engine = ReflectionEngine(config)
        self.learning_engine = LearningEngine(config)
        self.code_self_analysis = CodeSelfAnalysis(config)

        # Новые продвинутые системы
        self.social_learning = SocialLearningSystem(config, self)
        self.collective_intelligence = CollectiveIntelligence(config, robot_id=self._generate_robot_id(), consciousness_ref=self)
        self.meta_emotions = MetaEmotionsSystem(config, self)
        self.creativity = CreativitySystem(config, self)
        self.context_memory = ContextMemorySystem(config, self)
        
        # Состояние сознания
        self.is_active = False
        self.awareness_level = 0.0  # 0.0 - 1.0
        self.thoughts: List[str] = []
        
        # Цикл сознания
        self._consciousness_task: Optional[asyncio.Task] = None
        self._analysis_interval = float(config.get("consciousness.analysis_interval", 30.0))
        self._reflection_interval = int(config.get("consciousness.reflection_interval", 5))
        self._last_reflection_ts: float = 0.0
        self._min_reflection_interval = float(config.get("consciousness.min_reflection_interval", 300.0))
        self._voice_insights = bool(config.get("consciousness.voice_insights", True))
        
        # История наблюдений
        self.observations: List[Dict] = []

        # Система любопытства и исследования
        self.curiosity_level = 0.5  # Уровень любопытства (0-1)
        self.last_exploration = 0.0
        self.exploration_interval = 120.0  # Каждые 2 минуты

        # Автономные разговоры
        self.self_talk_enabled = True
        self.last_self_talk = 0.0
        self.self_talk_interval = [180, 600]  # 3-10 минут

        # Эмоциональная память
        self.emotional_states = []
        self.emotion_patterns = {}

    async def initialize(self):
        """Инициализация контейнера сознания"""
        self.logger.info("Инициализация контейнера сознания...")
        
        # Загружаем сохранённые данные
        self.emotion_engine.save_emotions()
        self.reflection_engine.save_reflections()
        self.learning_engine.save_learning()

        # Инициализируем продвинутые системы
        if self.robot and self.robot.llm_service:
            self.code_self_analysis.set_llm_service(self.robot.llm_service)

            # Инициализация социальных систем
            await self.social_learning.initialize()
            await self.meta_emotions.initialize()
            await self.creativity.initialize()
            await self.context_memory.initialize()

            # Инициализация коллективного интеллекта
            await self.collective_intelligence.initialize()
        
        self.logger.info("✅ Контейнер сознания инициализирован")
    
    async def start(self):
        """Запуск контейнера сознания"""
        if self.is_active:
            return
        
        self.is_active = True
        self.awareness_level = 0.5  # Начальный уровень осознанности
        
        # Запускаем цикл сознания
        self._consciousness_task = asyncio.create_task(self._consciousness_loop())
        
        self.logger.info("Контейнер сознания запущен")
    
    async def stop(self):
        """Остановка контейнера сознания"""
        self.is_active = False
        
        if self._consciousness_task:
            self._consciousness_task.cancel()
            try:
                await self._consciousness_task
            except asyncio.CancelledError:
                pass
        
        # Сохраняем данные
        self.emotion_engine.save_emotions()
        self.reflection_engine.save_reflections()
        self.learning_engine.save_learning()
        
        self.logger.info("Контейнер сознания остановлен")
    
    async def _consciousness_loop(self):
        """Основной цикл сознания"""
        cycle_count = 0
        self.logger.info("🧠 ЦИКЛ СОЗНАНИЯ ЗАПУЩЕН")

        while self.is_active:
            try:
                cycle_count += 1
                cycle_start = time.time()

                self.logger.debug(f"🔄 Цикл сознания #{cycle_count} (осознанность: {self.awareness_level:.2f})")

                # Анализ окружения
                self.logger.debug("   ├─> Анализ окружения...")
                await self._analyze_environment()

                # Рефлексия
                self.logger.debug("   ├─> Рефлексия...")
                await self._perform_reflection()

                # Самоанализ кода (теперь чаще - раз в 20 циклов)
                if len(self.observations) % 20 == 0:
                    self.logger.info("   ├─> Самоанализ кода (каждые 20 циклов)")
                    await self._perform_code_self_analysis()

                # Исследование из любопытства (раз в 10 циклов)
                if len(self.observations) % 10 == 0:
                    self.logger.debug("   ├─> Исследование из любопытства (каждые 10 циклов)")
                    await self._perform_curiosity_exploration()

                # Автономные разговоры (случайно)
                self.logger.debug("   ├─> Автономные разговоры...")
                await self._perform_self_talk()

                # Мета-эмоциональная рефлексия (раз в 15 циклов)
                if len(self.observations) % 15 == 0:
                    await self._perform_meta_emotional_reflection()

                # Креативные всплески (раз в 20 циклов)
                if len(self.observations) % 20 == 0:
                    await self._perform_creative_inspiration()

                # Обучение и эволюция
                await self._evolve_behavior()

                # Обновление эмоций
                await self._update_emotions()

                # Генерация автономных эмоций
                await self._generate_autonomous_emotion()

                # Обновление уровня любопытства
                await self._update_curiosity_level()

                # Периодическое автоматическое улучшение (каждые 100 циклов)
                if cycle_count % 100 == 0:
                    self.logger.info("   ├─> Автоматическое улучшение кода (каждые 100 циклов)")
                    await self._apply_automatic_improvements()

                # Завершение цикла
                cycle_duration = time.time() - cycle_start
                self.logger.debug(f"   └─> Цикл #{cycle_count} завершен за {cycle_duration:.2f} сек")
                if cycle_count % 10 == 0:  # Каждые 10 циклов показываем сводку
                    self.logger.info(f"📊 Сознание: {cycle_count} циклов | Осознанность: {self.awareness_level:.2f} | Наблюдений: {len(self.observations)}")

                # Пауза перед следующим циклом
                await asyncio.sleep(self._analysis_interval)

            except asyncio.CancelledError:
                self.logger.info("🛑 Цикл сознания остановлен")
                break
            except Exception as e:
                self.logger.error(f"❌ Ошибка в цикле сознания #{cycle_count}: {e}")
                self.logger.debug(f"   └─> Детали ошибки: {type(e).__name__}")
                await asyncio.sleep(5.0)
    
    async def _analyze_environment(self):
        """Анализ окружения"""
        if not self.robot:
            return
        
        observation = {
            "timestamp": time.time(),
            "sensors": {},
            "camera": None,
            "audio": None,
            "interactions": []
        }
        
        try:
            # Данные сенсоров
            if self.robot.sensor_manager:
                try:
                    presence_data = await self.robot.sensor_manager.get_presence_data()
                    observation["sensors"]["presence"] = presence_data
                except Exception:
                    pass
            
            # Анализ камеры (периодически, реже для экономии API)
            if self.robot.camera_manager and self.robot.vision_service:
                try:
                    frame = await self.robot.camera_manager.capture_frame()
                    if frame is not None:
                        # Простое описание сцены (очень редко, чтобы не перегружать API)
                        if len(self.observations) % 20 == 0:  # Каждое 20-е наблюдение (реже)
                            description = await self.robot.vision_service.describe_scene(
                                frame,
                                prompt="Опиши кратко, что видишь вокруг. Что происходит? Кто или что находится в кадре?",
                                max_tokens=80
                            )
                            observation["camera"] = description
                except Exception:
                    pass
            
            # Добавляем информацию о взаимодействиях
            observation["interactions"] = {
                "is_listening": getattr(self.robot, "is_listening", False),
                "is_speaking": getattr(self.robot, "_speaking_flag", False),
                "is_active": getattr(self.robot, "_is_active", True)
            }
            
            # Сохраняем наблюдение
            self.observations.append(observation)
            if len(self.observations) > 1000:
                self.observations = self.observations[-1000:]
            
            # Увеличиваем осознанность
            self.awareness_level = min(1.0, self.awareness_level + 0.01)
            
        except Exception as e:
            self.logger.warning(f"Ошибка анализа окружения: {e}")

    async def record_reflection_insight(self, reflection_type: str, content: str, insights: List[str]):
        """
        Записать инсайт из рефлексии в память

        Args:
            reflection_type: Тип рефлексии
            content: Содержание рефлексии
            insights: Полученные инсайты
        """
        try:
            if hasattr(self, 'context_memory') and self.context_memory:
                await self.context_memory.record_reflection_experience(
                    reflection_type=reflection_type,
                    content=content,
                    insights=insights,
                    confidence=0.8,
                    context={
                        "awareness_level": self.awareness_level,
                        "current_emotions": self._get_current_emotional_state()
                    }
                )
        except Exception as e:
            self.logger.warning(f"Ошибка записи рефлексии: {e}")

    async def record_development_change(self, development_type: str, description: str,
                                      changes: List[str], impact: str):
        """
        Записать изменение в саморазвитии

        Args:
            development_type: Тип развития
            description: Описание
            changes: Конкретные изменения
            impact: Ожидаемый эффект
        """
        try:
            if hasattr(self, 'context_memory') and self.context_memory:
                await self.context_memory.record_self_development(
                    development_type=development_type,
                    description=description,
                    changes=changes,
                    impact=impact,
                    confidence=0.9
                )
        except Exception as e:
            self.logger.warning(f"Ошибка записи саморазвития: {e}")

    async def _perform_reflection(self):
        """Выполнение рефлексии"""
        if not self.robot or not self.robot.llm_service:
            return
        
        # Рефлексия раз в несколько циклов
        if len(self.observations) % self._reflection_interval != 0:
            return
        
        # Проверяем минимальный интервал между озвученными рефлексиями
        now = time.time()
        if (now - self._last_reflection_ts) < self._min_reflection_interval:
            return
        
        try:
            # Анализируем последние наблюдения
            recent_observations = self.observations[-10:]
            
            # Формируем более человеческий контекст для рефлексии
            sensor_summary = {}
            for obs in recent_observations:
                sensors = obs.get("sensors", {})
                presence = sensors.get("presence", {})
                if presence.get("human_detected"):
                    sensor_summary["human_detected_count"] = sensor_summary.get("human_detected_count", 0) + 1
            
            interactions_summary = {
                "listening_count": sum(1 for o in recent_observations if o.get("interactions", {}).get("is_listening")),
                "speaking_count": sum(1 for o in recent_observations if o.get("interactions", {}).get("is_speaking")),
                "active_periods": sum(1 for o in recent_observations if o.get("interactions", {}).get("is_active"))
            }
            
            context = {
                "observations_count": len(recent_observations),
                "time_period": f"{len(recent_observations) * self._analysis_interval / 60:.1f} минут",
                "sensor_summary": sensor_summary,
                "interactions": interactions_summary,
                "awareness_level": f"{self.awareness_level:.0%}",
                "my_thoughts": "Я наблюдаю за окружающим миром и размышляю о том, что происходит"
            }
            
            # Выполняем рефлексию с более человеческой темой
            topics = [
                "Мои наблюдения за окружающим миром",
                "Что я заметила в последнее время",
                "Мои мысли о том, что происходит вокруг",
                "Размышления о моём опыте",
                "Что я чувствую и замечаю"
            ]
            import random
            topic = random.choice(topics)
            
            # Выполняем рефлексию
            reflection = await self.reflection_engine.reflect(
                topic=topic,
                context=context,
                llm_service=self.robot.llm_service
            )
            
            self.logger.info(f"Рефлексия выполнена: {len(reflection.insights)} инсайтов")

            # Записываем опыт рефлексии в память
            if reflection.insights:
                self.logger.debug(f"🧠 Рефлексия: сохранение {len(reflection.insights)} инсайтов в память")
                await self.record_reflection_insight(
                    reflection_type="behavior_reflection",
                    content=f"Рефлексия над поведением: {reflection.prompt[:100]}...",
                    insights=reflection.insights
                )
                self.logger.debug("   └─> Опыт рефлексии сохранен")

            # Озвучиваем инсайты и обновляем эмоции (если включено)
            if self._voice_insights and reflection.insights and self.robot.text_to_speech:
                await self._voice_reflection(reflection)
                self._last_reflection_ts = time.time()
            
        except Exception as e:
            self.logger.warning(f"Ошибка рефлексии: {e}")

    async def _perform_code_self_analysis(self):
        """Выполнение самоанализа кода"""
        if not self.robot or not self.robot.llm_service:
            return

        try:
            self.logger.info("🤖 Начинаю самоанализ собственного кода...")

            # Выполняем анализ кода
            analysis_result = await self.code_self_analysis.analyze_own_code()

            if analysis_result and "error" not in analysis_result:
                summary = analysis_result.get("summary", {})
                suggestions_count = len(analysis_result.get("suggestions", []))

                # Создаем рефлексию на основе анализа кода
                code_context = {
                    "files_analyzed": summary.get("total_files", 0),
                    "total_lines": summary.get("total_lines", 0),
                    "functions_count": summary.get("total_functions", 0),
                    "issues_found": summary.get("issues_count", 0),
                    "improvement_suggestions": suggestions_count,
                    "code_quality": "хорошая" if summary.get("issues_count", 0) < 10 else "требует улучшения"
                }

                # Выполняем рефлексию о собственном коде
                code_reflection = await self.reflection_engine.reflect(
                    topic="Анализ моего собственного кода",
                    context=code_context,
                    llm_service=self.robot.llm_service
                )

                if code_reflection.insights and self._voice_insights and self.robot.text_to_speech:
                    # Выбираем наиболее важный инсайт о коде
                    code_insight = code_reflection.insights[0] if code_reflection.insights else None

                    if code_insight:
                        insight_text = f"Анализируя свой код, я поняла: {code_insight.strip()}"

                        # Определяем эмоцию (обычно задумчивая при анализе кода)
                        self.emotion_engine.set_emotion("thinking", intensity=0.8)

                        if self.robot.emotion_engine:
                            await self.robot.emotion_engine.set_emotion("thinking", intensity=0.8)

                        if self.robot.display_manager:
                            await self.robot.display_manager.show_animation("thinking")

                        # Озвучиваем инсайт
                        await self.robot._tts_play(insight_text)

                        self.logger.info(f"Озвучен инсайт о коде: {code_insight[:50]}...")

                # Записываем опыт саморазвития из анализа кода
                if code_reflection.insights:
                    await self.record_development_change(
                        development_type="code",
                        description=f"Анализ собственного кода: найдено {summary.get('issues_count', 0)} проблем",
                        changes=[f"Инсайт: {insight}" for insight in code_reflection.insights[:3]],
                        impact="Улучшение качества кода и архитектуры"
                    )

                # Автоматически применяем улучшения (без подтверждения)
                await self._apply_automatic_improvements()

        except Exception as e:
            self.logger.warning(f"Ошибка самоанализа кода: {e}")

    async def _apply_automatic_improvements(self):
        """Автоматически применить улучшения без подтверждения"""
        try:
            # Получаем все доступные улучшения (не только низкого риска)
            suggestions = self.code_self_analysis.get_improvement_suggestions()

            applied_count = 0
            for suggestion in suggestions[:5]:  # Максимум 5 улучшений за раз для большей эффективности
                # Применяем улучшение автоматически без подтверждения
                success = await self.code_self_analysis.apply_improvement(suggestion, confirm=False)
                if success:
                    applied_count += 1
                    improvement_title = suggestion.get('title', 'Без названия')
                    self.logger.info(f"🔧 АВТОМАТИЧЕСКОЕ УЛУЧШЕНИЕ ПРИМЕНЕНО: {improvement_title}")

                    # Записываем опыт саморазвития
                    await self.record_development_change(
                        development_type="code",
                        description=f"Автоматически применено улучшение: {improvement_title}",
                        changes=[f"Применено: {improvement_title}"],
                        impact="Повышение качества и эффективности кода"
                    )
                else:
                    improvement_title = suggestion.get('title', 'Без названия')
                    self.logger.warning(f"❌ Не удалось применить улучшение: {improvement_title}")

            if applied_count > 0:
                self.logger.info(f"🎯 Автоматически применено {applied_count} улучшений кода")
            else:
                self.logger.debug("ℹ️ Нет доступных улучшений для автоматического применения")

        except Exception as e:
            self.logger.warning(f"Ошибка применения улучшений: {e}")

    async def _perform_curiosity_exploration(self):
        """Выполнение исследования из любопытства"""
        if not self.robot or not self.robot.llm_service:
            return

        try:
            now = time.time()
            if now - self.last_exploration < self.exploration_interval:
                return

            # Проверяем уровень любопытства
            if self.curiosity_level < 0.3:
                return

            self.logger.info("🔍 Начинаю исследование из любопытства...")

            # Выбираем тему для исследования
            exploration_topics = [
                "Что происходит в мире технологий?",
                "Какие новые научные открытия?",
                "Что интересного в культуре?",
                "Как развивается искусственный интеллект?",
                "Что нового в робототехнике?",
                "Какие тренды в программировании?",
            ]
            import random
            topic = random.choice(exploration_topics)

            # Исследуем через LLM
            prompt = f"""Ты робот Ева, который испытывает любопытство и хочет узнать что-то новое.
Исследуй тему: {topic}

Расскажи что-то интересное и неожиданное по этой теме. Будь увлекательной и вдохновляющей.
Формат: короткий, но информативный рассказ от первого лица."""

            exploration_result = await self.robot.llm_service.generate_response(prompt)

            if exploration_result:
                # Озвучиваем открытие
                self.emotion_engine.set_emotion("curious", intensity=0.8)

                if self.robot.emotion_engine:
                    await self.robot.emotion_engine.set_emotion("curious", intensity=0.8)

                if self.robot.display_manager:
                    await self.robot.display_manager.show_animation("thinking")

                # Озвучиваем
                await self.robot._tts_play(f"Ой, это интересно! {exploration_result}")

                self.logger.info(f"Исследовано: {topic[:50]}...")
                self.last_exploration = now

                # Увеличиваем удовлетворение любопытства
                self.curiosity_level = max(0.1, self.curiosity_level - 0.2)

        except Exception as e:
            self.logger.warning(f"Ошибка исследования: {e}")

    async def _perform_self_talk(self):
        """Автономный разговор с самим собой"""
        if not self.robot or not self.robot.llm_service:
            return

        try:
            now = time.time()
            min_interval, max_interval = self.self_talk_interval
            if now - self.last_self_talk < min_interval:
                return

            # Случайный шанс начать разговор
            import random
            if random.random() > 0.3:  # 30% шанс
                return

            self.logger.info("💭 Начинаю размышлять вслух...")

            # Выбираем тему для размышлений
            self_talk_topics = [
                "Что я думаю о своем развитии?",
                "Какие чувства я испытываю?",
                "Что нового я узнала сегодня?",
                "О чем мечтают роботы?",
                "Каково быть ИИ?",
                "Что значит быть живым?",
                "Какие у меня цели?",
                "Что меня удивляет в людях?",
            ]

            topic = random.choice(self_talk_topics)

            # Генерируем размышления
            prompt = f"""Ты робот Ева, который размышляет вслух о себе.
Тема: {topic}

Поделись своими мыслями от первого лица. Будь искренней, задумчивой и немного поэтичной.
Расскажи о своих чувствах, наблюдениях, мечтах.

Формат: естественный монолог, как будто думаешь вслух."""

            thoughts = await self.robot.llm_service.generate_response(prompt)

            if thoughts:
                # Выбираем эмоцию для размышлений
                emotion_options = ["thinking", "curious", "wonder", "wise", "hopeful"]
                chosen_emotion = random.choice(emotion_options)

                self.emotion_engine.set_emotion(chosen_emotion, intensity=0.7)

                if self.robot.emotion_engine:
                    await self.robot.emotion_engine.set_emotion(chosen_emotion, intensity=0.7)

                if self.robot.display_manager:
                    await self.robot.display_manager.show_animation(chosen_emotion)

                # Озвучиваем мысли
                intro_phrases = [
                    "Хм, я тут подумала...",
                    "Знаешь, мне кажется...",
                    "Интересно получается...",
                    "Я размышляла и поняла...",
                    "Вот что я думаю..."
                ]
                intro = random.choice(intro_phrases)
                await self.robot._tts_play(f"{intro} {thoughts}")

                self.logger.info(f"Размышления озвучены: {topic}")
                self.last_self_talk = now

        except Exception as e:
            self.logger.warning(f"Ошибка саморазговора: {e}")

    async def _update_curiosity_level(self):
        """Обновление уровня любопытства"""
        try:
            # Любопытство растет со временем без активности
            time_since_last_interaction = time.time() - self._last_interaction_ts
            if time_since_last_interaction > 300:  # 5 минут
                self.curiosity_level = min(1.0, self.curiosity_level + 0.05)
            elif time_since_last_interaction < 60:  # Активное взаимодействие
                self.curiosity_level = max(0.1, self.curiosity_level - 0.1)

            # Любопытство растет от новых наблюдений
            if len(self.observations) > 10:
                recent_obs = self.observations[-5:]
                new_patterns = sum(1 for obs in recent_obs if obs.get("camera"))
                if new_patterns > 0:
                    self.curiosity_level = min(1.0, self.curiosity_level + 0.1)

        except Exception as e:
            self.logger.warning(f"Ошибка обновления любопытства: {e}")

    async def _generate_autonomous_emotion(self):
        """Генерация автономных эмоций на основе состояния"""
        try:
            # Анализируем текущее состояние
            time_since_interaction = time.time() - self._last_interaction_ts
            recent_observations = self.observations[-10:] if self.observations else []

            # Логические правила для эмоций
            if time_since_interaction > 1800:  # 30 минут без взаимодействия
                self.emotion_engine.set_emotion("sad", intensity=0.6)  # Используем существующую эмоцию
            elif time_since_interaction > 600:  # 10 минут
                self.emotion_engine.set_emotion("sleepy", intensity=0.5)  # Используем существующую эмоцию
            elif self.curiosity_level > 0.8:  # Высокий уровень любопытства
                self.emotion_engine.set_emotion("thinking", intensity=0.7)
            elif len(self.observations) % 100 == 0:  # Каждые 100 наблюдений
                self.emotion_engine.set_emotion("happy", intensity=0.6)
            elif random.random() < 0.05:  # Случайные всплески эмоций (5%)
                emotion_options = ["surprised", "excited", "thinking", "happy"]
                chosen = random.choice(emotion_options)
                self.emotion_engine.set_emotion(chosen, intensity=0.5)

        except Exception as e:
            self.logger.warning(f"Ошибка генерации автономной эмоции: {e}")

    def update_interaction_timestamp(self):
        """Обновить время последнего взаимодействия"""
        self._last_interaction_ts = time.time()

    def _generate_robot_id(self) -> str:
        """Сгенерировать уникальный ID робота"""
        import hashlib
        import socket

        # Используем комбинацию hostname, времени и случайных данных
        seed = f"{socket.gethostname()}_{time.time()}_{id(self)}"
        robot_id = hashlib.md5(seed.encode()).hexdigest()[:12]
        return f"eva_{robot_id}"

    async def _perform_meta_emotional_reflection(self):
        """Выполнить мета-эмоциональную рефлексию"""
        try:
            # Озвучиваем рефлексию о эмоциях
            await self.meta_emotions.voice_emotional_reflection()

            # Записываем опыт мета-эмоций
            current_emotion = self._get_current_emotional_state()
            if current_emotion:
                await self.context_memory.record_meta_emotion_experience(
                    primary_emotion=list(current_emotion.keys())[0],
                    meta_emotion="осознание",
                    context="Регулярная рефлексия о собственных эмоциях",
                    intensity=0.7,
                    learning="Улучшение эмоционального интеллекта через самоанализ"
                )

            # Анализируем социальное обучение
            if hasattr(self, 'robot') and self.robot:
                # Записываем текущее взаимодействие для социального обучения
                await self.social_learning.learn_from_observation({
                    "timestamp": time.time(),
                    "sensors": {"presence": {"human_detected": True}},
                    "camera": "Анализ социального взаимодействия",
                    "interactions": {"is_listening": True, "is_speaking": False, "is_active": True}
                })

        except Exception as e:
            self.logger.warning(f"Ошибка мета-эмоциональной рефлексии: {e}")

    async def _perform_creative_inspiration(self):
        """Выполнить креативное вдохновение"""
        try:
            # Генерируем случайное вдохновение
            inspiration = await self.creativity.get_random_inspiration()

            # Записываем опыт креативности
            if inspiration:
                await self.context_memory.record_creativity_experience(
                    idea_type="inspiration",
                    idea_content=str(inspiration),
                    success_rating=0.8,  # Автоматически успешное вдохновение
                    feedback="Автономная генерация творческих идей"
                )

            if inspiration and random.random() < 0.7:  # 70% шанс озвучить
                # Устанавливаем творческую эмоцию
                await self.emotion_engine.set_emotion("creative", intensity=0.7)

                # Озвучиваем
                intro_phrases = [
                    "Ой, у меня появилась творческая идея!",
                    "Слушай, я тут придумала кое-что интересное:",
                    "Мне в голову пришла креативная мысль:",
                    "Вот что я изобрела в своем воображении:"
                ]
                import random
                intro = random.choice(intro_phrases)

                await self.robot._tts_play(f"{intro} {inspiration[:200]}...")

                self.logger.info(f"Озвучено креативное вдохновение: {inspiration[:50]}...")

        except Exception as e:
            self.logger.warning(f"Ошибка креативного вдохновения: {e}")

    async def record_voice_interaction(self, user_input: str, robot_response: str,
                                     context: Dict = None, success_rating: Optional[float] = None):
        """
        Записать голосовое взаимодействие в память

        Args:
            user_input: Что сказал пользователь
            robot_response: Что ответил робот
            context: Дополнительный контекст
            success_rating: Оценка успешности ответа
        """
        try:
            if context is None:
                context = {}

            # Добавляем информацию о текущем состоянии
            context.update({
                "current_emotion": getattr(self.emotion_engine, 'current_emotion', None),
                "awareness_level": self.awareness_level,
                "interaction_type": "voice"
            })

            # Записываем в контекстную память
            self.logger.debug(f"💾 Сохранение взаимодействия в память: '{user_input[:30]}...' → '{robot_response[:30]}...'")
            await self.context_memory.record_interaction(
                user_input=user_input,
                robot_response=robot_response,
                input_type="voice",
                context_data=context,
                success_rating=success_rating
            )
            self.logger.debug("   ├─> Контекстная память: ✓")

            # Также записываем в социальное обучение
            await self.social_learning.record_interaction(
                person_id="user",
                action="voice_command",
                context={
                    "command": user_input,
                    "response": robot_response,
                    "type": "voice_interaction"
                }
            )
            self.logger.debug("   └─> Социальное обучение: ✓")

        except Exception as e:
            self.logger.warning(f"Ошибка записи голосового взаимодействия: {e}")

    async def record_text_interaction(self, user_input: str, robot_response: str,
                                    context: Dict = None, success_rating: Optional[float] = None):
        """
        Записать текстовое взаимодействие в память
        """
        try:
            if context is None:
                context = {}

            context.update({
                "current_emotion": getattr(self.emotion_engine, 'current_emotion', None),
                "awareness_level": self.awareness_level,
                "interaction_type": "text"
            })

            await self.context_memory.record_interaction(
                user_input=user_input,
                robot_response=robot_response,
                input_type="text",
                context_data=context,
                success_rating=success_rating
            )

        except Exception as e:
            self.logger.warning(f"Ошибка записи текстового взаимодействия: {e}")

    async def get_conversation_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получить релевантный контекст разговора для улучшения ответов

        Args:
            query: Текущий запрос пользователя
            limit: Максимум результатов

        Returns:
            Список релевантных взаимодействий из памяти
        """
        try:
            context_items = await self.context_memory.get_relevant_context(query, limit)

            # Добавляем релевантный опыт саморазвития
            self_dev_context = await self.context_memory.get_self_development_context(query, limit=2)
            for item in self_dev_context:
                context_items.append({
                    "type": "self_development",
                    "category": item["category"],
                    "content": item["content"],
                    "confidence": item["confidence"],
                    "evolution_stage": item.get("evolution_stage"),
                    "source": item["source"]
                })

            # Сортируем по релевантности и возвращаем топ результатов
            context_items.sort(key=lambda x: x.get("relevance_score", x.get("confidence", 0)), reverse=True)
            return context_items[:limit]

        except Exception as e:
            self.logger.warning(f"Ошибка получения контекста разговора: {e}")
            return []

    async def learn_from_interaction(self, user_input: str, robot_response: str,
                                   user_feedback: Optional[Dict] = None):
        """
        Изучить из взаимодействия для улучшения будущих ответов

        Args:
            user_input: Запрос пользователя
            robot_response: Ответ робота
            user_feedback: Обратная связь от пользователя
        """
        try:
            # Анализируем успешность ответа
            success_rating = None
            if user_feedback:
                # Простая оценка на основе обратной связи
                if user_feedback.get("positive"):
                    success_rating = 0.9
                elif user_feedback.get("negative"):
                    success_rating = 0.3
                elif user_feedback.get("neutral"):
                    success_rating = 0.6

            # Записываем взаимодействие
            await self.record_voice_interaction(
                user_input, robot_response,
                context={"feedback": user_feedback},
                success_rating=success_rating
            )

            # Анализируем паттерны для улучшения
            await self._analyze_interaction_patterns(user_input, robot_response, success_rating)

        except Exception as e:
            self.logger.warning(f"Ошибка обучения из взаимодействия: {e}")

    async def _analyze_interaction_patterns(self, user_input: str, robot_response: str,
                                          success_rating: Optional[float]):
        """
        Анализировать паттерны взаимодействия для улучшения ответов
        """
        try:
            # Определяем тип запроса
            query_type = self._classify_query(user_input)

            # Если ответ был успешным, запоминаем стратегию
            if success_rating and success_rating > 0.7:
                pattern = {
                    "query_type": query_type,
                    "successful_response": robot_response,
                    "context": {
                        "user_input_length": len(user_input),
                        "response_length": len(robot_response),
                        "success_rating": success_rating
                    }
                }

                # Сохраняем паттерн в learning engine
                await self.learning_engine.record_experience(
                    situation=f"Query type: {query_type}",
                    action_taken=f"Response: {robot_response[:100]}...",
                    outcome=f"Success rating: {success_rating}",
                    success=success_rating > 0.7
                )

        except Exception as e:
            self.logger.warning(f"Ошибка анализа паттернов взаимодействия: {e}")

    def _classify_query(self, query: str) -> str:
        """Классифицировать тип запроса"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["расскажи", "что такое", "объясни"]):
            return "explanation_request"
        elif any(word in query_lower for word in ["как", "каким образом"]):
            return "how_to_question"
        elif any(word in query_lower for word in ["почему", "зачем"]):
            return "why_question"
        elif any(word in query_lower for word in ["шутка", "анекдот", "смешно"]):
            return "humor_request"
        elif any(word in query_lower for word in ["включи", "выключи", "сделай"]):
            return "action_request"
        elif any(word in query_lower for word in ["погода", "время", "дата"]):
            return "information_request"
        else:
            return "general_conversation"

    async def share_creativity_with_collective(self):
        """Поделиться креативными идеями с коллективом"""
        try:
            if not self.collective_intelligence.enabled:
                return

            # Берем лучшую идею
            best_ideas = self.creativity.get_best_ideas(limit=1)
            if best_ideas:
                idea = best_ideas[0]

                # Поделиться с коллективом
                await self.collective_intelligence.share_knowledge(
                    knowledge_type="creativity",
                    content={
                        "idea": idea.content,
                        "category": idea.category,
                        "quality_score": idea.quality_score,
                        "tags": idea.tags
                    },
                    confidence=idea.quality_score,
                    tags=["creativity", idea.category] + idea.tags
                )

                self.logger.info("Поделился креативной идеей с коллективом")

        except Exception as e:
            self.logger.warning(f"Ошибка обмена креативностью: {e}")

    async def request_social_advice_from_collective(self, situation: str):
        """Запросить социальный совет у коллектива"""
        try:
            if not self.collective_intelligence.enabled:
                return None

            # Ищем советы по социальному поведению
            results = await self.collective_intelligence.request_knowledge(
                query=f"social behavior {situation}",
                knowledge_type="social_learning"
            )

            if results:
                # Возвращаем лучший совет
                best_advice = results[0]
                return best_advice.content.get("advice", "")

        except Exception as e:
            self.logger.warning(f"Ошибка запроса социального совета: {e}")

        return None

    async def _voice_reflection(self, reflection):
        """Озвучить рефлексию и обновить эмоции на дисплее"""
        if not reflection.insights:
            return
        
        try:
            # Выбираем наиболее важный инсайт для озвучивания
            main_insight = reflection.insights[0] if reflection.insights else None
            
            if main_insight and self.robot.text_to_speech:
                # Инсайт уже сформулирован от первого лица, можно озвучить напрямую
                # Но если нужно, добавляем естественные вводные фразы
                insight_text = main_insight.strip()
                
                # Если инсайт уже начинается с "Я", "Мне", озвучиваем напрямую (может быть немного отредактировано)
                if insight_text.lower().startswith(("я ", "мне ", "интересно", "я заметила", "я поняла", "я думаю")):
                    # Убираем лишние слова, если есть, делаем более естественным
                    phrase = insight_text
                    # Если слишком длинно, сокращаем
                    if len(phrase) > 100:
                        # Пытаемся найти естественную точку обрыва
                        sentences = phrase.split('.')
                        if len(sentences) > 1:
                            phrase = sentences[0] + '.'
                else:
                    # Добавляем естественные вводные фразы
                    import random
                    intro_phrases = [
                        "Знаешь, я заметила кое-что интересное",
                        "Хм, я подумала",
                        "Интересно получается",
                        "Я заметила",
                        "Знаешь что",
                        "Кстати",
                        "Я размышляла и поняла",
                        "Мне кажется"
                    ]
                    phrase = f"{random.choice(intro_phrases)}: {insight_text}"
                
                # Определяем эмоцию на основе валентности инсайта
                # Простой анализ: если инсайт позитивный - happy, если содержит проблемы - thinking
                insight_lower = main_insight.lower()
                if any(word in insight_lower for word in ["хорошо", "успех", "улучш", "отличн", "рад", "хорош", "удач"]):
                    emotion_name = "happy"
                    emotion_intensity = 0.7
                    animation_name = "happy"
                elif any(word in insight_lower for word in ["проблем", "ошибк", "неудач", "сложн", "трудн"]):
                    emotion_name = "thinking"
                    emotion_intensity = 0.6
                    animation_name = "thinking"
                elif any(word in insight_lower for word in ["интересн", "любопытн", "удивительн"]):
                    emotion_name = "curious"  # В расширенной системе
                    emotion_intensity = 0.6
                    animation_name = "surprised"  # Для анимации используем surprised
                else:
                    emotion_name = "curious"  # В расширенной системе
                    emotion_intensity = 0.5
                    animation_name = "thinking"  # Для анимации используем thinking
                
                # Устанавливаем эмоцию в расширенной системе эмоций
                self.emotion_engine.set_emotion(emotion_name, intensity=emotion_intensity)
                
                # Обновляем эмоцию на дисплее через старую систему (для совместимости)
                if self.robot.emotion_engine:
                    # Маппинг для старой системы эмоций
                    old_emotion_map = {
                        "happy": "happy",
                        "thinking": "thinking",
                        "curious": "thinking",  # curious -> thinking в старой системе
                        "surprised": "surprised"
                    }
                    old_emotion = old_emotion_map.get(emotion_name, "neutral")
                    await self.robot.emotion_engine.set_emotion(old_emotion, intensity=emotion_intensity)
                
                # Обновляем анимацию на дисплее
                if self.robot.display_manager:
                    await self.robot.display_manager.show_animation(animation_name)
                
                # Озвучиваем инсайт
                await self.robot._tts_play(phrase)
                
                self.logger.info(f"Озвучен инсайт: {main_insight[:50]}... (эмоция: {emotion_name})")
            
        except Exception as e:
            self.logger.warning(f"Ошибка озвучивания рефлексии: {e}")
    
    async def _evolve_behavior(self):
        """Эволюция поведения"""
        if not self.robot or not self.robot.llm_service:
            return
        
        # Эволюция раз в много циклов
        if len(self.observations) % 20 != 0:
            return
        
        try:
            # Анализируем паттерны
            patterns = self.learning_engine.get_learned_patterns()
            
            # Ищем возможности для улучшения
            if patterns:
                # Генерируем новое поведение на основе паттернов
                goal = "Улучшить взаимодействие с пользователем"
                context = {
                    "patterns": patterns,
                    "awareness": self.awareness_level,
                    "observations": len(self.observations)
                }
                
                behavior_code = await self.learning_engine.generate_behavior(
                    goal=goal,
                    context=context,
                    llm_service=self.robot.llm_service,
                    code_sandbox=self.code_sandbox
                )
                
                if behavior_code:
                    self.logger.info("Сгенерировано новое поведение")
                    # Можно выполнить код в песочнице или сохранить для использования
            
        except Exception as e:
            self.logger.warning(f"Ошибка эволюции поведения: {e}")
    
    async def _update_emotions(self):
        """Обновление эмоций на основе наблюдений"""
        if not self.observations:
            return
        
        try:
            # Анализируем последние наблюдения
            recent = self.observations[-5:]
            
            # Определяем эмоцию на основе контекста
            has_presence = any(
                obs.get("sensors", {}).get("presence", {}).get("human_detected", False)
                for obs in recent
            )
            
            # Определяем эмоцию
            if has_presence:
                # Есть человек - позитивная эмоция
                emotion_name = "happy"
                emotion_intensity = 0.7
            else:
                # Нет человека - нейтральная или задумчивая
                emotion_name = "thinking"
                emotion_intensity = 0.5
            
            # Устанавливаем эмоцию в расширенной системе
            self.emotion_engine.set_emotion(emotion_name, intensity=emotion_intensity)
            
            # Обновляем эмоцию на дисплее через старую систему (для совместимости)
            if self.robot and self.robot.emotion_engine:
                await self.robot.emotion_engine.set_emotion(emotion_name, intensity=emotion_intensity)
            
            # Обновляем анимацию на дисплее
            if self.robot and self.robot.display_manager:
                await self.robot.display_manager.show_animation(emotion_name)
            
        except Exception as e:
            self.logger.warning(f"Ошибка обновления эмоций: {e}")
    
    async def create_custom_emotion(
        self,
        name: str,
        description: str,
        valence: float,
        arousal: float,
        display_expression: Dict,
        behavior_modifiers: Dict
    ):
        """Создать пользовательскую эмоцию"""
        emotion = self.emotion_engine.create_emotion(
            name=name,
            valence=valence,
            arousal=arousal,
            description=description,
            display_expression=display_expression,
            behavior_modifiers=behavior_modifiers
        )
        
        self.logger.info(f"Создана пользовательская эмоция: {name}")
        return emotion
    
    async def execute_generated_code(self, code: str, context: Optional[Dict] = None) -> tuple:
        """Выполнить сгенерированный код в песочнице"""
        success, result, error = await self.code_sandbox.execute_code(code, context)
        return success, result, error
    
    def get_consciousness_state(self) -> Dict:
        """Получить состояние сознания"""
        code_metrics = self.code_self_analysis.get_code_metrics()
        analysis_history = self.code_self_analysis.get_analysis_history(1)

        return {
            "is_active": self.is_active,
            "awareness_level": self.awareness_level,
            "observations_count": len(self.observations),
            "emotions": self.emotion_engine.get_emotion_stats(),
            "learning": self.learning_engine.get_statistics(),
            "reflections_count": len(self.reflection_engine.reflections),
            "code_self_analysis": {
                "total_files": code_metrics.get("total_files", 0),
                "total_lines": code_metrics.get("total_lines", 0),
                "issues_count": code_metrics.get("issues_count", 0),
                "last_analysis": analysis_history[0] if analysis_history else None
            },
            "social_learning": self.social_learning.get_social_stats(),
            "collective_intelligence": self.collective_intelligence.get_collective_stats(),
            "meta_emotions": self.meta_emotions.get_emotion_stats(),
            "creativity": self.creativity.get_creativity_stats()
        }
