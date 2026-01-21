"""
Система социального обучения - изучение поведения людей
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
class HumanBehavior:
    """Запись поведения человека"""
    timestamp: float
    person_id: str
    action: str
    context: Dict[str, Any]
    robot_response: Optional[str] = None
    human_reaction: Optional[str] = None
    success_rating: Optional[float] = None


@dataclass
class PersonProfile:
    """Профиль человека"""
    person_id: str
    name: Optional[str] = None
    preferences: Dict[str, Any] = None
    interaction_patterns: Dict[str, Any] = None
    emotional_responses: Dict[str, Any] = None
    last_seen: float = 0.0
    interaction_count: int = 0

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.interaction_patterns is None:
            self.interaction_patterns = {}
        if self.emotional_responses is None:
            self.emotional_responses = {}


class SocialLearningSystem:
    """
    Система социального обучения

    Изучает:
    - Поведение людей
    - Предпочтения в общении
    - Реакции на действия робота
    - Эмоциональные паттерны
    - Адаптируется под индивидуальные особенности
    """

    def __init__(self, config, consciousness_ref=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.consciousness = consciousness_ref

        # Пути к данным
        self.data_path = "/home/pi/Projects/RobotEva/data/social_learning"
        self.behaviors_file = os.path.join(self.data_path, "behaviors.json")
        self.profiles_file = os.path.join(self.data_path, "person_profiles.json")

        # Данные
        self.behaviors: List[HumanBehavior] = []
        self.person_profiles: Dict[str, PersonProfile] = {}
        self.current_person_id: Optional[str] = None

        # Статистика
        self.learning_stats = {
            "total_interactions": 0,
            "unique_persons": 0,
            "learned_patterns": 0,
            "adaptation_success_rate": 0.0
        }

        # Настройки
        self.max_behaviors = 10000
        self.max_profiles = 100
        self.adaptation_threshold = 0.7  # Порог уверенности для адаптации

        # Создаем директорию
        os.makedirs(self.data_path, exist_ok=True)

        # Загружаем данные
        self._load_data()

    async def initialize(self):
        """Инициализация системы"""
        self.logger.info("Инициализация системы социального обучения")
        await self._load_data_async()
        self.logger.info(f"Загружено {len(self.behaviors)} поведений, {len(self.person_profiles)} профилей")

    def _load_data(self):
        """Загрузка данных из файлов"""
        try:
            # Загружаем поведения
            if os.path.exists(self.behaviors_file):
                with open(self.behaviors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.behaviors = [HumanBehavior(**b) for b in data.get("behaviors", [])]

            # Загружаем профили
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pid, profile_data in data.get("profiles", {}).items():
                        self.person_profiles[pid] = PersonProfile(**profile_data)

        except Exception as e:
            self.logger.warning(f"Ошибка загрузки данных социального обучения: {e}")

    async def _load_data_async(self):
        """Асинхронная загрузка данных"""
        # Можно добавить дополнительную логику загрузки
        pass

    def save_data(self):
        """Сохранение данных"""
        try:
            # Сохраняем поведения
            behaviors_data = {
                "behaviors": [asdict(b) for b in self.behaviors[-self.max_behaviors:]],
                "saved_at": time.time()
            }
            with open(self.behaviors_file, 'w', encoding='utf-8') as f:
                json.dump(behaviors_data, f, indent=2, ensure_ascii=False)

            # Сохраняем профили
            profiles_data = {
                "profiles": {pid: asdict(profile) for pid, profile in self.person_profiles.items()},
                "saved_at": time.time()
            }
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2, ensure_ascii=False)

            self.logger.debug("Данные социального обучения сохранены")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных социального обучения: {e}")

    async def record_interaction(self, person_id: str, action: str, context: Dict,
                               robot_response: Optional[str] = None) -> HumanBehavior:
        """
        Записать взаимодействие с человеком

        Args:
            person_id: ID человека
            action: Действие человека
            context: Контекст взаимодействия
            robot_response: Ответ робота (если есть)
        """
        behavior = HumanBehavior(
            timestamp=time.time(),
            person_id=person_id,
            action=action,
            context=context,
            robot_response=robot_response
        )

        self.behaviors.append(behavior)
        self.current_person_id = person_id

        # Ограничиваем количество записей
        if len(self.behaviors) > self.max_behaviors:
            self.behaviors = self.behaviors[-self.max_behaviors:]

        # Обновляем профиль человека
        await self._update_person_profile(behavior)

        # Анализируем паттерны
        await self._analyze_patterns(person_id)

        # Сохраняем
        self.save_data()

        self.learning_stats["total_interactions"] += 1
        return behavior

    async def _update_person_profile(self, behavior: HumanBehavior):
        """Обновить профиль человека"""
        person_id = behavior.person_id

        if person_id not in self.person_profiles:
            self.person_profiles[person_id] = PersonProfile(person_id=person_id)
            self.learning_stats["unique_persons"] += 1

        profile = self.person_profiles[person_id]
        profile.last_seen = behavior.timestamp
        profile.interaction_count += 1

        # Обновляем предпочтения
        await self._update_preferences(profile, behavior)

        # Ограничиваем количество профилей
        if len(self.person_profiles) > self.max_profiles:
            # Удаляем самые старые профили
            oldest = min(self.person_profiles.keys(),
                        key=lambda x: self.person_profiles[x].last_seen)
            del self.person_profiles[oldest]

    async def _update_preferences(self, profile: PersonProfile, behavior: HumanBehavior):
        """Обновить предпочтения человека"""
        action = behavior.action
        context = behavior.context

        # Анализируем время дня
        hour = time.localtime(behavior.timestamp).tm_hour
        time_of_day = self._get_time_of_day(hour)

        # Анализируем тип взаимодействия
        interaction_type = context.get("type", "unknown")

        # Обновляем паттерны
        if "time_patterns" not in profile.preferences:
            profile.preferences["time_patterns"] = defaultdict(int)
        profile.preferences["time_patterns"][time_of_day] += 1

        if "interaction_types" not in profile.preferences:
            profile.preferences["interaction_types"] = defaultdict(int)
        profile.preferences["interaction_types"][interaction_type] += 1

        # Анализируем успешность взаимодействий
        if behavior.success_rating is not None:
            if "successful_actions" not in profile.preferences:
                profile.preferences["successful_actions"] = defaultdict(list)
            profile.preferences["successful_actions"][action].append(behavior.success_rating)

    def _get_time_of_day(self, hour: int) -> str:
        """Определить время суток"""
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"

    async def _analyze_patterns(self, person_id: str):
        """Анализировать паттерны поведения человека"""
        if person_id not in self.person_profiles:
            return

        profile = self.person_profiles[person_id]

        # Анализируем последние взаимодействия
        recent_behaviors = [b for b in self.behaviors[-50:]
                          if b.person_id == person_id]

        if len(recent_behaviors) < 5:
            return  # Недостаточно данных

        # Находим паттерны
        patterns = self._find_behavior_patterns(recent_behaviors)

        # Обновляем interaction_patterns
        profile.interaction_patterns.update(patterns)

        self.learning_stats["learned_patterns"] += len(patterns)

    def _find_behavior_patterns(self, behaviors: List[HumanBehavior]) -> Dict[str, Any]:
        """Найти паттерны в поведении"""
        patterns = {}

        # Анализируем последовательности действий
        actions = [b.action for b in behaviors]
        if len(actions) >= 3:
            # Ищем повторяющиеся последовательности
            sequences = self._find_sequences(actions)
            if sequences:
                patterns["common_sequences"] = sequences[:3]  # Топ-3

        # Анализируем время между взаимодействиями
        if len(behaviors) >= 2:
            intervals = []
            for i in range(1, len(behaviors)):
                interval = behaviors[i].timestamp - behaviors[i-1].timestamp
                intervals.append(interval)

            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                patterns["avg_interaction_interval"] = avg_interval

        # Анализируем предпочтения по времени
        time_preferences = {}
        for behavior in behaviors:
            hour = time.localtime(behavior.timestamp).tm_hour
            time_slot = f"{hour//2*2:02d}-{(hour//2*2+2):02d}h"
            time_preferences[time_slot] = time_preferences.get(time_slot, 0) + 1

        if time_preferences:
            best_time = max(time_preferences.keys(), key=lambda x: time_preferences[x])
            patterns["preferred_time"] = best_time

        return patterns

    def _find_sequences(self, actions: List[str]) -> List[List[str]]:
        """Найти повторяющиеся последовательности"""
        sequences = []
        min_length = 2
        max_length = 4

        for length in range(min_length, min_length + max_length):
            if length > len(actions) // 2:
                break

            for i in range(len(actions) - length + 1):
                seq = actions[i:i+length]
                count = 0

                # Считаем сколько раз последовательность повторяется
                for j in range(len(actions) - length + 1):
                    if actions[j:j+length] == seq:
                        count += 1

                if count >= 2:  # Повторяется как минимум 2 раза
                    sequences.append(seq)

        # Убираем дубликаты и сортируем по частоте
        unique_sequences = []
        seen = set()
        for seq in sequences:
            seq_tuple = tuple(seq)
            if seq_tuple not in seen:
                unique_sequences.append(seq)
                seen.add(seq_tuple)

        return unique_sequences

    async def get_adapted_response(self, person_id: str, current_context: Dict) -> Optional[Dict]:
        """
        Получить адаптированный ответ для человека

        Args:
            person_id: ID человека
            current_context: Текущий контекст

        Returns:
            Рекомендации по адаптации или None
        """
        if person_id not in self.person_profiles:
            return None

        profile = self.person_profiles[person_id]

        # Анализируем предпочтения
        recommendations = {}

        # Временные предпочтения
        if "preferred_time" in profile.interaction_patterns:
            current_hour = time.localtime().tm_hour
            preferred = profile.interaction_patterns["preferred_time"]
            pref_start = int(preferred.split('-')[0][:2])

            if abs(current_hour - pref_start) > 2:
                recommendations["time_adaptation"] = f"Человек предпочитает взаимодействовать около {preferred}"

        # Предпочтения по типам взаимодействия
        interaction_types = profile.preferences.get("interaction_types", {})
        if interaction_types:
            preferred_type = max(interaction_types.keys(), key=lambda x: interaction_types[x])
            recommendations["preferred_interaction"] = preferred_type

        # Успешные действия
        successful_actions = profile.preferences.get("successful_actions", {})
        if successful_actions:
            best_actions = sorted(successful_actions.items(),
                                key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0,
                                reverse=True)
            if best_actions:
                recommendations["recommended_actions"] = best_actions[0][0]

        return recommendations if recommendations else None

    async def predict_human_behavior(self, person_id: str, current_situation: Dict) -> Optional[str]:
        """
        Предсказать следующее поведение человека

        Args:
            person_id: ID человека
            current_situation: Текущая ситуация

        Returns:
            Предсказанное действие или None
        """
        if person_id not in self.person_profiles:
            return None

        profile = self.person_profiles[person_id]
        patterns = profile.interaction_patterns

        # Анализируем последовательности
        common_sequences = patterns.get("common_sequences", [])
        if common_sequences and len(common_sequences) > 0:
            # Берем наиболее вероятную последовательность
            likely_sequence = common_sequences[0]

            # Если последовательность достаточно длинная, предсказываем следующее действие
            if len(likely_sequence) >= 3:
                # Это упрощенная логика - в реальности нужна более сложная модель
                return f"Возможно, человек продолжит паттерн: {likely_sequence}"

        return None

    async def learn_from_observation(self, observation: Dict):
        """
        Изучить поведение из наблюдения

        Args:
            observation: Наблюдение от системы сознания
        """
        # Анализируем сенсорные данные
        sensors = observation.get("sensors", {})
        presence_data = sensors.get("presence", {})

        if presence_data.get("human_detected"):
            person_id = f"person_{int(time.time())}"  # Временный ID

            # Определяем тип поведения на основе данных
            action = self._classify_observation(observation)

            if action:
                context = {
                    "type": "observation",
                    "sensors": sensors,
                    "camera": observation.get("camera"),
                    "timestamp": observation["timestamp"]
                }

                await self.record_interaction(person_id, action, context)

    def _classify_observation(self, observation: Dict) -> Optional[str]:
        """Классифицировать наблюдение"""
        # Анализируем данные для определения типа поведения
        sensors = observation.get("sensors", {})
        camera_desc = observation.get("camera", "")

        # Простая классификация на основе описания
        if "разговаривает" in camera_desc or "говорит" in camera_desc:
            return "talking"
        elif "смотрит" in camera_desc or "глядит" in camera_desc:
            return "looking"
        elif "улыбается" in camera_desc or "смеется" in camera_desc:
            return "smiling"
        elif "жестикулирует" in camera_desc:
            return "gesturing"
        elif "сидит" in camera_desc:
            return "sitting"
        elif "стоит" in camera_desc:
            return "standing"
        else:
            return "present"

    def get_social_stats(self) -> Dict[str, Any]:
        """Получить статистику социального обучения"""
        return {
            "total_interactions": self.learning_stats["total_interactions"],
            "unique_persons": len(self.person_profiles),
            "learned_patterns": self.learning_stats["learned_patterns"],
            "active_profiles": len([p for p in self.person_profiles.values()
                                  if time.time() - p.last_seen < 86400*7]),  # Активные за неделю
            "adaptation_confidence": self.learning_stats["adaptation_success_rate"]
        }

    def get_person_insights(self, person_id: str) -> Optional[Dict[str, Any]]:
        """Получить инсайты о человеке"""
        if person_id not in self.person_profiles:
            return None

        profile = self.person_profiles[person_id]

        insights = {
            "name": profile.name,
            "interaction_count": profile.interaction_count,
            "last_seen": profile.last_seen,
            "time_since_last_seen": time.time() - profile.last_seen,
            "preferences": dict(profile.preferences),
            "patterns": dict(profile.interaction_patterns)
        }

        # Добавляем интерпретацию
        if profile.interaction_patterns.get("preferred_time"):
            insights["preferred_time_interpretation"] = (
                f"Предпочитает взаимодействовать около {profile.interaction_patterns['preferred_time']}"
            )

        return insights