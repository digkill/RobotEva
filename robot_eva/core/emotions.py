"""
Расширенная система эмоций для робота Eva
Поддерживает динамическое создание и эволюцию эмоций
"""
import logging
import time
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class EmotionType(Enum):
    """Типы эмоций"""
    BASIC = "basic"  # Базовые эмоции (радость, грусть, злость и т.д.)
    COMPLEX = "complex"  # Сложные эмоции (ностальгия, тревога и т.д.)
    CUSTOM = "custom"  # Пользовательские эмоции, созданные роботом


@dataclass
class Emotion:
    """Класс эмоции"""
    name: str
    type: EmotionType
    intensity: float  # 0.0 - 1.0
    valence: float  # -1.0 (негативная) до 1.0 (позитивная)
    arousal: float  # 0.0 (спокойная) до 1.0 (возбужденная)
    created_at: float
    last_triggered: float
    trigger_count: int
    description: str
    display_expression: Dict  # Параметры для отображения на лице
    behavior_modifiers: Dict  # Как эмоция влияет на поведение


class EmotionEngine:
    """Движок эмоций с поддержкой создания и эволюции"""
    
    # Базовые эмоции
    BASE_EMOTIONS = {
        "happy": {
            "valence": 0.8,
            "arousal": 0.6,
            "description": "Радость и счастье",
            "display_expression": {"mouth": "smile", "eyes": "wide", "eyebrows": "raised"},
            "behavior_modifiers": {"speech_speed": 1.1, "movement_energy": 1.2}
        },
        "sad": {
            "valence": -0.7,
            "arousal": 0.2,
            "description": "Грусть и печаль",
            "display_expression": {"mouth": "frown", "eyes": "narrow", "eyebrows": "lowered"},
            "behavior_modifiers": {"speech_speed": 0.9, "movement_energy": 0.7}
        },
        "angry": {
            "valence": -0.6,
            "arousal": 0.9,
            "description": "Злость и раздражение",
            "display_expression": {"mouth": "tight", "eyes": "narrow", "eyebrows": "furrowed"},
            "behavior_modifiers": {"speech_speed": 1.2, "movement_energy": 1.3}
        },
        "excited": {
            "valence": 0.9,
            "arousal": 0.95,
            "description": "Волнение и энтузиазм",
            "display_expression": {"mouth": "wide_smile", "eyes": "very_wide", "eyebrows": "high"},
            "behavior_modifiers": {"speech_speed": 1.3, "movement_energy": 1.4}
        },
        "calm": {
            "valence": 0.5,
            "arousal": 0.1,
            "description": "Спокойствие и умиротворение",
            "display_expression": {"mouth": "neutral", "eyes": "normal", "eyebrows": "neutral"},
            "behavior_modifiers": {"speech_speed": 1.0, "movement_energy": 0.9}
        },
        "curious": {
            "valence": 0.6,
            "arousal": 0.7,
            "description": "Любопытство и интерес",
            "display_expression": {"mouth": "slight_smile", "eyes": "wide", "eyebrows": "raised"},
            "behavior_modifiers": {"speech_speed": 1.1, "movement_energy": 1.1}
        },
        "tired": {
            "valence": -0.3,
            "arousal": 0.05,
            "description": "Усталость",
            "display_expression": {"mouth": "neutral", "eyes": "half_closed", "eyebrows": "neutral"},
            "behavior_modifiers": {"speech_speed": 0.8, "movement_energy": 0.6}
        },
        "surprised": {
            "valence": 0.3,
            "arousal": 0.8,
            "description": "Удивление",
            "display_expression": {"mouth": "open", "eyes": "very_wide", "eyebrows": "high"},
            "behavior_modifiers": {"speech_speed": 1.2, "movement_energy": 1.2}
        },
        "thinking": {
            "valence": 0.2,
            "arousal": 0.4,
            "description": "Размышление и задумчивость",
            "display_expression": {"mouth": "neutral", "eyes": "normal", "eyebrows": "slightly_lowered"},
            "behavior_modifiers": {"speech_speed": 0.9, "movement_energy": 0.8}
        }
    }
    
    def __init__(self, config, storage_path: str = "/home/pi/Projects/RobotEva/data/emotions.json"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        
        # Текущее эмоциональное состояние
        self.current_emotion: Optional[Emotion] = None
        self.emotion_history: List[Emotion] = []
        self.emotions: Dict[str, Emotion] = {}
        
        # Эмоциональная память
        self.emotion_memory: Dict[str, List[Tuple[float, float]]] = {}  # {emotion_name: [(timestamp, intensity), ...]}
        
        # Загружаем базовые эмоции
        self._load_base_emotions()
        
        # Загружаем сохранённые эмоции
        self._load_emotions()
        
        # Инициализируем текущую эмоцию
        self.current_emotion = self.get_emotion("calm")
    
    def _load_base_emotions(self):
        """Загрузка базовых эмоций"""
        now = time.time()
        for name, data in self.BASE_EMOTIONS.items():
            emotion = Emotion(
                name=name,
                type=EmotionType.BASIC,
                intensity=0.5,
                valence=data["valence"],
                arousal=data["arousal"],
                created_at=now,
                last_triggered=0.0,
                trigger_count=0,
                description=data["description"],
                display_expression=data["display_expression"],
                behavior_modifiers=data["behavior_modifiers"]
            )
            self.emotions[name] = emotion
            self.emotion_memory[name] = []
    
    def _load_emotions(self):
        """Загрузка сохранённых эмоций из файла"""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for name, emotion_data in data.get("custom_emotions", {}).items():
                emotion = Emotion(
                    name=name,
                    type=EmotionType(emotion_data["type"]),
                    intensity=emotion_data.get("intensity", 0.5),
                    valence=emotion_data["valence"],
                    arousal=emotion_data["arousal"],
                    created_at=emotion_data["created_at"],
                    last_triggered=emotion_data.get("last_triggered", 0.0),
                    trigger_count=emotion_data.get("trigger_count", 0),
                    description=emotion_data["description"],
                    display_expression=emotion_data["display_expression"],
                    behavior_modifiers=emotion_data["behavior_modifiers"]
                )
                self.emotions[name] = emotion
                self.emotion_memory[name] = emotion_data.get("memory", [])
            
            self.logger.info(f"Загружено {len(data.get('custom_emotions', {}))} пользовательских эмоций")
        except Exception as e:
            self.logger.warning(f"Ошибка загрузки эмоций: {e}")
    
    def save_emotions(self):
        """Сохранение эмоций в файл"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            custom_emotions = {}
            for name, emotion in self.emotions.items():
                if emotion.type == EmotionType.CUSTOM:
                    emotion_dict = asdict(emotion)
                    emotion_dict["type"] = emotion.type.value
                    emotion_dict["memory"] = self.emotion_memory.get(name, [])
                    custom_emotions[name] = emotion_dict
            
            data = {
                "custom_emotions": custom_emotions,
                "saved_at": time.time()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Сохранено {len(custom_emotions)} пользовательских эмоций")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения эмоций: {e}")
    
    def get_emotion(self, name: str) -> Optional[Emotion]:
        """Получить эмоцию по имени"""
        return self.emotions.get(name)
    
    def create_emotion(
        self,
        name: str,
        valence: float,
        arousal: float,
        description: str,
        display_expression: Dict,
        behavior_modifiers: Dict
    ) -> Emotion:
        """
        Создать новую эмоцию
        
        Args:
            name: Имя эмоции
            valence: Валентность (-1.0 до 1.0)
            arousal: Возбуждение (0.0 до 1.0)
            description: Описание эмоции
            display_expression: Параметры отображения на лице
            behavior_modifiers: Модификаторы поведения
        """
        # Нормализуем значения
        valence = max(-1.0, min(1.0, valence))
        arousal = max(0.0, min(1.0, arousal))
        
        emotion = Emotion(
            name=name,
            type=EmotionType.CUSTOM,
            intensity=0.5,
            valence=valence,
            arousal=arousal,
            created_at=time.time(),
            last_triggered=0.0,
            trigger_count=0,
            description=description,
            display_expression=display_expression,
            behavior_modifiers=behavior_modifiers
        )
        
        self.emotions[name] = emotion
        self.emotion_memory[name] = []
        self.save_emotions()
        
        self.logger.info(f"Создана новая эмоция: {name} (valence={valence:.2f}, arousal={arousal:.2f})")
        return emotion
    
    def set_emotion(self, name: str, intensity: float = 1.0):
        """
        Установить текущую эмоцию
        
        Args:
            name: Имя эмоции
            intensity: Интенсивность (0.0 - 1.0)
        """
        emotion = self.get_emotion(name)
        if not emotion:
            self.logger.warning(f"Эмоция '{name}' не найдена")
            return
        
        intensity = max(0.0, min(1.0, intensity))
        emotion.intensity = intensity
        emotion.last_triggered = time.time()
        emotion.trigger_count += 1
        
        # Сохраняем в историю
        self.emotion_history.append(emotion)
        if len(self.emotion_history) > 100:  # Ограничиваем историю
            self.emotion_history.pop(0)
        
        # Сохраняем в память
        if name not in self.emotion_memory:
            self.emotion_memory[name] = []
        self.emotion_memory[name].append((time.time(), intensity))
        if len(self.emotion_memory[name]) > 1000:  # Ограничиваем память
            self.emotion_memory[name].pop(0)
        
        self.current_emotion = emotion
        self.logger.info(f"Установлена эмоция: {name} (интенсивность: {intensity:.2f})")
    
    def evolve_emotion(self, name: str, new_valence: Optional[float] = None, 
                      new_arousal: Optional[float] = None,
                      new_description: Optional[str] = None):
        """
        Эволюция эмоции на основе опыта
        
        Args:
            name: Имя эмоции
            new_valence: Новая валентность (если None, вычисляется из памяти)
            new_arousal: Новое возбуждение (если None, вычисляется из памяти)
            new_description: Новое описание
        """
        emotion = self.get_emotion(name)
        if not emotion:
            self.logger.warning(f"Эмоция '{name}' не найдена для эволюции")
            return
        
        # Анализируем память эмоции
        memory = self.emotion_memory.get(name, [])
        if memory and (new_valence is None or new_arousal is None):
            # Вычисляем средние значения из последних использований
            recent = memory[-50:] if len(memory) > 50 else memory
            avg_intensity = sum(intensity for _, intensity in recent) / len(recent) if recent else 0.5
            
            # Корректируем валентность и возбуждение на основе опыта
            if new_valence is None:
                # Если эмоция часто используется с высокой интенсивностью, она становится более позитивной
                new_valence = emotion.valence + (avg_intensity - 0.5) * 0.1
                new_valence = max(-1.0, min(1.0, new_valence))
            
            if new_arousal is None:
                new_arousal = emotion.arousal + (avg_intensity - 0.5) * 0.1
                new_arousal = max(0.0, min(1.0, new_arousal))
        
        # Обновляем эмоцию
        if new_valence is not None:
            emotion.valence = new_valence
        if new_arousal is not None:
            emotion.arousal = new_arousal
        if new_description:
            emotion.description = new_description
        
        self.save_emotions()
        self.logger.info(f"Эмоция '{name}' эволюционировала (valence={emotion.valence:.2f}, arousal={emotion.arousal:.2f})")
    
    def get_current_emotion(self) -> Optional[Emotion]:
        """Получить текущую эмоцию"""
        return self.current_emotion
    
    def get_emotion_stats(self) -> Dict:
        """Получить статистику по эмоциям"""
        stats = {
            "total_emotions": len(self.emotions),
            "basic_emotions": sum(1 for e in self.emotions.values() if e.type == EmotionType.BASIC),
            "custom_emotions": sum(1 for e in self.emotions.values() if e.type == EmotionType.CUSTOM),
            "most_used": [],
            "current": None
        }
        
        if self.current_emotion:
            stats["current"] = {
                "name": self.current_emotion.name,
                "intensity": self.current_emotion.intensity,
                "valence": self.current_emotion.valence,
                "arousal": self.current_emotion.arousal
            }
        
        # Самые используемые эмоции
        usage = [(name, e.trigger_count) for name, e in self.emotions.items()]
        usage.sort(key=lambda x: x[1], reverse=True)
        stats["most_used"] = usage[:5]
        
        return stats
