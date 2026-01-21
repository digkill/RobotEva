"""
Система обучения и эволюции для робота
"""
import logging
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict


@dataclass
class LearningExperience:
    """Опыт обучения"""
    timestamp: float
    situation: str
    action_taken: str
    outcome: str
    success: bool
    learned_pattern: Optional[str] = None


class LearningEngine:
    """Движок обучения и эволюции"""
    
    def __init__(self, config, storage_path: str = "/home/pi/Projects/RobotEva/data/learning.json"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        
        self.experiences: List[LearningExperience] = []
        self.patterns: Dict[str, Dict] = {}  # Выученные паттерны
        self.behaviors: Dict[str, str] = {}  # Сгенерированные поведения
        
        # Загружаем сохранённые данные
        self._load_learning()
    
    def _load_learning(self):
        """Загрузка данных обучения"""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.experiences = [
                LearningExperience(**e) for e in data.get("experiences", [])
            ]
            self.patterns = data.get("patterns", {})
            self.behaviors = data.get("behaviors", {})
            
            self.logger.info(f"Загружено {len(self.experiences)} опытов обучения")
        except Exception as e:
            self.logger.warning(f"Ошибка загрузки обучения: {e}")
    
    def save_learning(self):
        """Сохранение данных обучения"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            data = {
                "experiences": [asdict(e) for e in self.experiences],
                "patterns": self.patterns,
                "behaviors": self.behaviors,
                "saved_at": time.time()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Сохранено {len(self.experiences)} опытов")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения обучения: {e}")
    
    def record_experience(
        self,
        situation: str,
        action_taken: str,
        outcome: str,
        success: bool
    ) -> LearningExperience:
        """Записать опыт обучения"""
        experience = LearningExperience(
            timestamp=time.time(),
            situation=situation,
            action_taken=action_taken,
            outcome=outcome,
            success=success
        )
        
        self.experiences.append(experience)
        
        # Ограничиваем количество опытов
        if len(self.experiences) > 10000:
            self.experiences = self.experiences[-10000:]
        
        # Анализируем паттерны
        self._analyze_patterns(experience)
        
        # Сохраняем
        self.save_learning()
        
        return experience
    
    def _analyze_patterns(self, experience: LearningExperience):
        """Анализ паттернов из опыта"""
        # Ищем похожие ситуации
        similar = [
            e for e in self.experiences[-100:]  # Последние 100 опытов
            if e.situation == experience.situation and e != experience
        ]
        
        if len(similar) >= 2:
            # Нашли паттерн
            success_rate = sum(1 for e in similar if e.success) / len(similar)
            
            pattern_key = f"pattern_{experience.situation[:20]}"
            self.patterns[pattern_key] = {
                "situation": experience.situation,
                "success_rate": success_rate,
                "count": len(similar) + 1,
                "last_updated": time.time()
            }
            
            experience.learned_pattern = pattern_key
            self.logger.info(f"Обнаружен паттерн: {pattern_key} (успешность: {success_rate:.2%})")
    
    async def generate_behavior(
        self,
        goal: str,
        context: Dict[str, Any],
        llm_service: Optional[Any] = None,
        code_sandbox: Optional[Any] = None
    ) -> Optional[str]:
        """
        Генерация нового поведения для достижения цели
        
        Args:
            goal: Цель поведения
            context: Контекст (доступные ресурсы, текущее состояние)
            llm_service: Сервис LLM для генерации
            code_sandbox: Песочница для выполнения кода
        
        Returns:
            Код поведения или None
        """
        if not llm_service:
            self.logger.warning("LLM сервис недоступен для генерации поведения")
            return None
        
        try:
            # Анализируем похожие опыты
            similar_experiences = self._find_similar_experiences(goal, context)
            
            # Формируем промпт
            prompt = f"""Создай Python функцию для робота, которая поможет достичь цели.

Цель: {goal}

Контекст:
{json.dumps(context, indent=2, ensure_ascii=False)}

Похожие опыты:
{self._format_experiences(similar_experiences)}

Требования:
1. Функция должна быть асинхронной (async def)
2. Используй только безопасные операции
3. Код должен быть простым и понятным
4. Функция должна возвращать результат

Сгенерируй только код функции, без объяснений."""
            
            code = await llm_service.generate_response(prompt, max_tokens=500)
            if not code:
                return None
            
            # Очищаем код от markdown разметки
            code = self._clean_code(code)
            
            # Валидируем и тестируем код
            if code_sandbox:
                is_valid, error = code_sandbox.validate_code(code)
                if not is_valid:
                    self.logger.warning(f"Сгенерированный код не прошёл валидацию: {error}")
                    return None
            
            # Сохраняем поведение
            behavior_id = f"behavior_{int(time.time())}"
            self.behaviors[behavior_id] = code
            self.save_learning()
            
            self.logger.info(f"Сгенерировано новое поведение: {behavior_id}")
            return code
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации поведения: {e}")
            return None
    
    def _find_similar_experiences(self, goal: str, context: Dict) -> List[LearningExperience]:
        """Найти похожие опыты"""
        # Простой поиск по ключевым словам
        goal_words = set(goal.lower().split())
        
        similar = []
        for exp in self.experiences[-500:]:  # Последние 500 опытов
            exp_words = set(exp.situation.lower().split())
            if goal_words & exp_words:  # Есть пересечение
                similar.append(exp)
        
        return similar[:10]  # Возвращаем до 10 похожих
    
    def _format_experiences(self, experiences: List[LearningExperience]) -> str:
        """Форматирование опытов для промпта"""
        if not experiences:
            return "Нет похожих опытов"
        
        lines = []
        for exp in experiences[:5]:  # До 5 опытов
            status = "✓" if exp.success else "✗"
            lines.append(f"{status} {exp.situation} -> {exp.action_taken} -> {exp.outcome}")
        
        return "\n".join(lines)
    
    def _clean_code(self, code: str) -> str:
        """Очистка кода от markdown и лишнего"""
        # Убираем markdown блоки
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        # Убираем лишние пробелы
        code = code.strip()
        
        return code
    
    def get_learned_patterns(self) -> Dict[str, Dict]:
        """Получить выученные паттерны"""
        return self.patterns
    
    def get_behaviors(self) -> Dict[str, str]:
        """Получить сгенерированные поведения"""
        return self.behaviors
    
    def get_statistics(self) -> Dict:
        """Получить статистику обучения"""
        total = len(self.experiences)
        successful = sum(1 for e in self.experiences if e.success)
        
        return {
            "total_experiences": total,
            "successful_experiences": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "learned_patterns": len(self.patterns),
            "generated_behaviors": len(self.behaviors)
        }
