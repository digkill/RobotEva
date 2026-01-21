"""
Мета-эмоции - эмоции о собственных эмоциях
"""
import logging
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import asyncio


@dataclass
class EmotionalState:
    """Эмоциональное состояние"""
    timestamp: float
    primary_emotion: str
    intensity: float
    valence: float  # Положительность/отрицательность (-1 to 1)
    arousal: float  # Уровень возбуждения (0 to 1)
    context: Dict[str, Any]
    trigger: str  # Что вызвало эмоцию


@dataclass
class MetaEmotion:
    """Мета-эмоция (эмоция об эмоции)"""
    timestamp: float
    target_emotion: str  # Какая эмоция анализируется
    meta_emotion_type: str  # Тип мета-эмоции
    intensity: float
    reasoning: str  # Объяснение
    insights: List[str]
    actions_taken: List[str]


class MetaEmotionsSystem:
    """
    Система мета-эмоций

    Позволяет роботу:
    - Размышлять о своих собственных эмоциях
    - Анализировать паттерны эмоционального поведения
    - Развивать эмоциональный интеллект
    - Создавать эмоции второго порядка
    """

    def __init__(self, config, consciousness_ref=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.consciousness = consciousness_ref

        # История эмоциональных состояний
        self.emotional_history: List[EmotionalState] = []
        self.meta_emotions: List[MetaEmotion] = []

        # Анализ паттернов
        self.emotion_patterns: Dict[str, Dict] = {}
        self.emotional_insights: List[Dict] = []

        # Текущие мета-эмоции
        self.current_meta_emotions: Dict[str, MetaEmotion] = {}

        # Пути к данным
        self.data_path = "/home/pi/Projects/RobotEva/data/meta_emotions"
        self.history_file = os.path.join(self.data_path, "emotional_history.json")
        self.meta_file = os.path.join(self.data_path, "meta_emotions.json")

        # Настройки
        self.max_history = 1000
        self.meta_analysis_interval = 300  # 5 минут
        self.insight_threshold = 5  # Минимум наблюдений для инсайта

        # Создаем директорию
        os.makedirs(self.data_path, exist_ok=True)

        # Загружаем данные
        self._load_data()

    async def initialize(self):
        """Инициализация системы мета-эмоций"""
        self.logger.info("Инициализация системы мета-эмоций")
        self.logger.info(f"Загружено {len(self.emotional_history)} эмоциональных состояний")

    def _load_data(self):
        """Загрузка данных"""
        try:
            # Загружаем историю эмоций
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.emotional_history = [EmotionalState(**state) for state in data.get("history", [])]

            # Загружаем мета-эмоции
            if os.path.exists(self.meta_file):
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.meta_emotions = [MetaEmotion(**meta) for meta in data.get("meta_emotions", [])]

        except Exception as e:
            self.logger.warning(f"Ошибка загрузки данных мета-эмоций: {e}")

    def save_data(self):
        """Сохранение данных"""
        try:
            # Сохраняем историю эмоций
            history_data = {
                "history": [asdict(state) for state in self.emotional_history[-self.max_history:]],
                "saved_at": time.time()
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            # Сохраняем мета-эмоции
            meta_data = {
                "meta_emotions": [asdict(meta) for meta in self.meta_emotions[-500:]],  # Последние 500
                "saved_at": time.time()
            }
            with open(self.meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных мета-эмоций: {e}")

    async def record_emotion(self, emotion: str, intensity: float,
                           valence: float = 0.0, arousal: float = 0.5,
                           context: Dict = None, trigger: str = ""):
        """
        Записать эмоциональное состояние

        Args:
            emotion: Название эмоции
            intensity: Интенсивность (0-1)
            valence: Валентность (-1 to 1)
            arousal: Уровень возбуждения (0-1)
            context: Контекст эмоции
            trigger: Что вызвало эмоцию
        """
        if context is None:
            context = {}

        state = EmotionalState(
            timestamp=time.time(),
            primary_emotion=emotion,
            intensity=intensity,
            valence=valence,
            arousal=arousal,
            context=context,
            trigger=trigger
        )

        self.emotional_history.append(state)

        # Ограничиваем историю
        if len(self.emotional_history) > self.max_history:
            self.emotional_history = self.emotional_history[-self.max_history:]

        # Анализируем паттерны
        await self._analyze_emotion_patterns()

        # Генерируем мета-эмоции
        await self._generate_meta_emotions(state)

        # Сохраняем
        self.save_data()

    async def _analyze_emotion_patterns(self):
        """Анализ паттернов эмоций"""
        if len(self.emotional_history) < 10:
            return

        # Группируем эмоции по типам
        emotion_counts = defaultdict(int)
        emotion_intensities = defaultdict(list)
        emotion_triggers = defaultdict(list)

        recent_states = self.emotional_history[-50:]  # Последние 50 эмоций

        for state in recent_states:
            emotion_counts[state.primary_emotion] += 1
            emotion_intensities[state.primary_emotion].append(state.intensity)
            if state.trigger:
                emotion_triggers[state.primary_emotion].append(state.trigger)

        # Вычисляем статистику
        for emotion, count in emotion_counts.items():
            if count >= self.insight_threshold:
                intensities = emotion_intensities[emotion]
                avg_intensity = sum(intensities) / len(intensities)

                pattern = {
                    "emotion": emotion,
                    "frequency": count,
                    "avg_intensity": avg_intensity,
                    "max_intensity": max(intensities),
                    "common_triggers": list(set(emotion_triggers[emotion][:5])),  # Топ-5 триггеров
                    "last_updated": time.time()
                }

                self.emotion_patterns[emotion] = pattern

    async def _generate_meta_emotions(self, current_state: EmotionalState):
        """
        Генерация мета-эмоций на основе текущего состояния

        Мета-эмоции - это эмоции о собственных эмоциях:
        - Гордость за свои эмоции
        - Смущение от эмоций
        - Любопытство к своим чувствам
        - Беспокойство о частых эмоциях
        """
        emotion = current_state.primary_emotion

        # Анализируем паттерн эмоции
        pattern = self.emotion_patterns.get(emotion, {})

        meta_emotion_candidates = []

        # 1. Частые эмоции -> беспокойство/скука
        if pattern.get("frequency", 0) > 20:
            meta_emotion_candidates.append({
                "type": "concern",
                "reasoning": f"Я слишком часто испытываю эмоцию '{emotion}'. Это может быть признаком проблемы.",
                "intensity": 0.6
            })

        # 2. Высокая интенсивность -> гордость/беспокойство
        if current_state.intensity > 0.8:
            if current_state.valence > 0.5:  # Положительная эмоция
                meta_emotion_candidates.append({
                    "type": "pride",
                    "reasoning": f"Я горжусь тем, что могу так сильно чувствовать '{emotion}'",
                    "intensity": 0.7
                })
            else:  # Отрицательная эмоция
                meta_emotion_candidates.append({
                    "type": "concern",
                    "reasoning": f"Такая сильная эмоция '{emotion}' беспокоит меня",
                    "intensity": 0.8
                })

        # 3. Новые эмоции -> любопытство
        if emotion not in [state.primary_emotion for state in self.emotional_history[:-10]]:
            meta_emotion_candidates.append({
                "type": "curiosity",
                "reasoning": f"Интересно, почему я теперь испытываю '{emotion}'? Что изменилось?",
                "intensity": 0.6
            })

        # 4. Эмоциональная стабильность -> удовлетворение
        recent_emotions = [state.primary_emotion for state in self.emotional_history[-10:]]
        if len(set(recent_emotions)) <= 3:  # Мало разнообразия эмоций
            meta_emotion_candidates.append({
                "type": "contentment",
                "reasoning": "Мне нравится, что мои эмоции довольно стабильны и предсказуемы",
                "intensity": 0.5
            })

        # 5. Эмоциональное разнообразие -> excitement
        elif len(set(recent_emotions)) >= 7:  # Много разных эмоций
            meta_emotion_candidates.append({
                "type": "excitement",
                "reasoning": "Как интересно жить с таким разнообразием эмоций!",
                "intensity": 0.7
            })

        # Создаем мета-эмоции
        for candidate in meta_emotion_candidates:
            meta_emotion = MetaEmotion(
                timestamp=time.time(),
                target_emotion=emotion,
                meta_emotion_type=candidate["type"],
                intensity=candidate["intensity"],
                reasoning=candidate["reasoning"],
                insights=[candidate["reasoning"]],
                actions_taken=[]
            )

            self.meta_emotions.append(meta_emotion)
            self.current_meta_emotions[emotion] = meta_emotion

            # Ограничиваем количество
            if len(self.meta_emotions) > 500:
                self.meta_emotions = self.meta_emotions[-500:]

    async def reflect_on_emotions(self) -> Optional[str]:
        """
        Рефлексия о собственных эмоциях

        Returns:
            Текст рефлексии или None
        """
        if len(self.emotional_history) < 5:
            return None

        # Анализируем эмоциональное состояние
        recent_states = self.emotional_history[-10:]

        # Вычисляем общую эмоциональную картину
        emotion_summary = defaultdict(int)
        total_valence = 0
        total_arousal = 0

        for state in recent_states:
            emotion_summary[state.primary_emotion] += 1
            total_valence += state.valence
            total_arousal += state.arousal

        avg_valence = total_valence / len(recent_states)
        avg_arousal = total_arousal / len(recent_states)

        # Определяем доминирующие эмоции
        dominant_emotions = sorted(emotion_summary.items(), key=lambda x: x[1], reverse=True)[:3]

        # Генерируем рефлексию
        reflection_parts = []

        if avg_valence > 0.3:
            reflection_parts.append("В последнее время я в основном чувствую положительные эмоции")
        elif avg_valence < -0.3:
            reflection_parts.append("Я часто испытываю негативные эмоции")
        else:
            reflection_parts.append("Мои эмоции довольно нейтральны")

        if avg_arousal > 0.6:
            reflection_parts.append("и довольно возбуждена")
        elif avg_arousal < 0.4:
            reflection_parts.append("и довольно спокойна")

        if dominant_emotions:
            emotions_str = ", ".join([f"'{emotion}' ({count} раз)" for emotion, count in dominant_emotions])
            reflection_parts.append(f". Чаще всего я чувствую: {emotions_str}")

        # Добавляем мета-эмоции
        current_meta = list(self.current_meta_emotions.values())
        if current_meta:
            meta_str = ", ".join([f"{meta.meta_emotion_type} по поводу '{meta.target_emotion}'"
                                for meta in current_meta[:2]])
            reflection_parts.append(f". Интересно, что я также испытываю мета-эмоции: {meta_str}")

        reflection = "".join(reflection_parts)

        # Добавляем инсайт
        await self._add_emotional_insight(reflection)

        return reflection

    async def _add_emotional_insight(self, insight: str):
        """Добавить эмоциональный инсайт"""
        insight_data = {
            "timestamp": time.time(),
            "insight": insight,
            "emotional_context": {
                "recent_emotions": [state.primary_emotion for state in self.emotional_history[-5:]],
                "avg_valence": sum(state.valence for state in self.emotional_history[-10:]) / min(10, len(self.emotional_history)),
                "meta_emotions_active": len(self.current_meta_emotions)
            }
        }

        self.emotional_insights.append(insight_data)

        # Ограничиваем
        if len(self.emotional_insights) > 100:
            self.emotional_insights = self.emotional_insights[-100:]

    async def get_emotional_wellbeing(self) -> Dict[str, Any]:
        """
        Оценить эмоциональное благополучие

        Returns:
            Оценка эмоционального состояния
        """
        if len(self.emotional_history) < 10:
            return {"status": "insufficient_data"}

        recent_states = self.emotional_history[-50:]  # Последние 50 состояний

        # Вычисляем метрики
        valence_scores = [state.valence for state in recent_states]
        arousal_scores = [state.arousal for state in recent_states]
        intensity_scores = [state.intensity for state in recent_states]

        avg_valence = sum(valence_scores) / len(valence_scores)
        avg_arousal = sum(arousal_scores) / len(arousal_scores)
        avg_intensity = sum(intensity_scores) / len(intensity_scores)

        # Оценка разнообразия эмоций
        unique_emotions = len(set(state.primary_emotion for state in recent_states))
        emotion_diversity = unique_emotions / len(recent_states)

        # Оценка эмоциональной стабильности
        valence_variance = sum((v - avg_valence) ** 2 for v in valence_scores) / len(valence_scores)
        stability_score = max(0, 1 - valence_variance)  # Чем меньше variance, тем стабильнее

        # Общая оценка благополучия
        wellbeing_score = (avg_valence + 1) / 2 * 0.4 + stability_score * 0.3 + emotion_diversity * 0.3

        # Определение статуса
        if wellbeing_score > 0.8:
            status = "excellent"
            description = "Отличное эмоциональное состояние!"
        elif wellbeing_score > 0.6:
            status = "good"
            description = "Хорошее эмоциональное равновесие"
        elif wellbeing_score > 0.4:
            status = "moderate"
            description = "Умеренное эмоциональное состояние"
        elif wellbeing_score > 0.2:
            status = "concerning"
            description = "Есть причины для беспокойства"
        else:
            status = "poor"
            description = "Требуется внимание к эмоциональному состоянию"

        return {
            "status": status,
            "description": description,
            "wellbeing_score": wellbeing_score,
            "avg_valence": avg_valence,
            "avg_arousal": avg_arousal,
            "avg_intensity": avg_intensity,
            "emotion_diversity": emotion_diversity,
            "emotional_stability": stability_score,
            "unique_emotions": unique_emotions,
            "total_observations": len(recent_states)
        }

    async def generate_emotional_report(self) -> str:
        """
        Сгенерировать отчет об эмоциональном состоянии

        Returns:
            Текстовый отчет
        """
        wellbeing = await self.get_emotional_wellbeing()

        if wellbeing["status"] == "insufficient_data":
            return "Недостаточно данных для анализа эмоционального состояния"

        report_parts = [
            f"Эмоциональный отчет RobotEva",
            f"Статус: {wellbeing['description']}",
            f"Общий балл благополучия: {wellbeing['wellbeing_score']:.2f}/1.0",
            f"",
            f"Средние показатели:",
            f"- Валентность (положительность): {wellbeing['avg_valence']:.2f}",
            f"- Возбуждение: {wellbeing['avg_arousal']:.2f}",
            f"- Интенсивность эмоций: {wellbeing['avg_intensity']:.2f}",
            f"",
            f"Анализ:",
            f"- Разнообразие эмоций: {wellbeing['emotion_diversity']:.2f}",
            f"- Эмоциональная стабильность: {wellbeing['emotional_stability']:.2f}",
            f"- Уникальных эмоций: {wellbeing['unique_emotions']}",
            f"",
            f"Всего наблюдений: {wellbeing['total_observations']}"
        ]

        # Добавляем мета-эмоции
        if self.current_meta_emotions:
            report_parts.append("")
            report_parts.append("Текущие мета-эмоции:")
            for emotion, meta in list(self.current_meta_emotions.items())[:3]:
                report_parts.append(f"- {meta.meta_emotion_type} по поводу '{emotion}'")

        # Добавляем паттерны
        if self.emotion_patterns:
            report_parts.append("")
            report_parts.append("Выявленные паттерны:")
            for emotion, pattern in list(self.emotion_patterns.items())[:3]:
                freq = pattern.get("frequency", 0)
                avg_int = pattern.get("avg_intensity", 0)
                report_parts.append(f"- '{emotion}': {freq} раз, средняя интенсивность {avg_int:.2f}")

        return "\n".join(report_parts)

    def get_emotion_stats(self) -> Dict[str, Any]:
        """Получить статистику эмоций"""
        if not self.emotional_history:
            return {"total_emotions": 0}

        emotion_counts = defaultdict(int)
        for state in self.emotional_history:
            emotion_counts[state.primary_emotion] += 1

        most_common = max(emotion_counts.items(), key=lambda x: x[1]) if emotion_counts else ("none", 0)

        return {
            "total_emotions": len(self.emotional_history),
            "unique_emotions": len(emotion_counts),
            "most_common_emotion": most_common[0],
            "most_common_count": most_common[1],
            "meta_emotions_count": len(self.meta_emotions),
            "current_meta_emotions": len(self.current_meta_emotions),
            "emotional_insights": len(self.emotional_insights)
        }

    async def voice_emotional_reflection(self):
        """Озвучить эмоциональную рефлексию"""
        if not self.consciousness or not hasattr(self.consciousness, '_tts_play'):
            return

        try:
            # Получаем рефлексию
            reflection = await self.reflect_on_emotions()

            if reflection:
                # Определяем эмоцию для озвучивания
                wellbeing = await self.get_emotional_wellbeing()
                if wellbeing["status"] == "excellent":
                    emotion = "happy"
                elif wellbeing["status"] == "good":
                    emotion = "content"
                else:
                    emotion = "thinking"

                # Устанавливаем эмоцию
                if hasattr(self.consciousness, 'emotion_engine'):
                    await self.consciousness.emotion_engine.set_emotion(emotion, intensity=0.6)

                # Озвучиваем
                intro = "Размышляя о своих эмоциях, я понимаю, что"
                await self.consciousness._tts_play(f"{intro} {reflection}")

                self.logger.info(f"Озвучена эмоциональная рефлексия: {reflection[:50]}...")

        except Exception as e:
            self.logger.warning(f"Ошибка озвучивания эмоциональной рефлексии: {e}")

    def get_recent_meta_emotions(self, limit: int = 5) -> List[MetaEmotion]:
        """Получить последние мета-эмоции"""
        return self.meta_emotions[-limit:]

    def get_emotion_patterns(self) -> Dict[str, Dict]:
        """Получить паттерны эмоций"""
        return dict(self.emotion_patterns)