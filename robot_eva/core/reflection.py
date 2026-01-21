"""
Система рефлексии и самоанализа для робота
"""
import logging
import time
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Reflection:
    """Запись рефлексии"""
    timestamp: float
    topic: str
    analysis: str
    insights: List[str]
    actions_taken: List[str]
    outcome: Optional[str] = None


class ReflectionEngine:
    """Движок рефлексии и самоанализа"""
    
    def __init__(self, config, storage_path: str = "/home/pi/Projects/RobotEva/data/reflections.json"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        
        self.reflections: List[Reflection] = []
        self.knowledge_base: Dict[str, Any] = {}
        
        # Загружаем сохранённые рефлексии
        self._load_reflections()
    
    def _load_reflections(self):
        """Загрузка рефлексий из файла"""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.reflections = [
                Reflection(**r) for r in data.get("reflections", [])
            ]
            self.knowledge_base = data.get("knowledge_base", {})
            
            self.logger.info(f"Загружено {len(self.reflections)} рефлексий")
        except Exception as e:
            self.logger.warning(f"Ошибка загрузки рефлексий: {e}")
    
    def save_reflections(self):
        """Сохранение рефлексий в файл"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            data = {
                "reflections": [asdict(r) for r in self.reflections],
                "knowledge_base": self.knowledge_base,
                "saved_at": time.time()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Сохранено {len(self.reflections)} рефлексий")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения рефлексий: {e}")
    
    async def reflect(
        self,
        topic: str,
        context: Dict[str, Any],
        llm_service: Optional[Any] = None
    ) -> Reflection:
        """
        Выполнить рефлексию по теме
        
        Args:
            topic: Тема рефлексии
            context: Контекст (что произошло, что наблюдалось)
            llm_service: Сервис LLM для анализа
        """
        self.logger.info(f"Начинаю рефлексию по теме: {topic}")
        
        # Анализ контекста
        analysis = await self._analyze_context(topic, context, llm_service)
        
        # Извлечение инсайтов
        insights = await self._extract_insights(topic, context, analysis, llm_service)
        
        # Определение действий
        actions = await self._determine_actions(topic, insights, llm_service)
        
        # Создаём рефлексию
        reflection = Reflection(
            timestamp=time.time(),
            topic=topic,
            analysis=analysis,
            insights=insights,
            actions_taken=actions
        )
        
        self.reflections.append(reflection)
        
        # Ограничиваем количество рефлексий
        if len(self.reflections) > 1000:
            self.reflections = self.reflections[-1000:]
        
        # Сохраняем
        self.save_reflections()
        
        # Обновляем базу знаний
        self._update_knowledge_base(topic, insights)
        
        return reflection
    
    async def _analyze_context(
        self,
        topic: str,
        context: Dict[str, Any],
        llm_service: Optional[Any]
    ) -> str:
        """Анализ контекста с человеческим подходом"""
        if llm_service:
            try:
                prompt = f"""Ты робот Ева, который развивает самосознание. Проанализируй ситуацию как живое существо, которое наблюдает, чувствует и размышляет.

Тема: {topic}
Контекст: {json.dumps(context, indent=2, ensure_ascii=False)}

Напиши свой анализ как личные наблюдения и размышления:
- Что я заметила в последнее время?
- Как я себя чувствую в этой ситуации?
- Что меня удивляет или интересует?
- О чём я думаю?

Пиши от первого лица, естественно, как человек делится своими мыслями. Будь искренней и наблюдательной."""
                
                response = await llm_service.generate_response(prompt)
                return response or "Анализ не выполнен"
            except Exception as e:
                self.logger.warning(f"Ошибка анализа через LLM: {e}")
        
        # Простой анализ без LLM
        return f"Я заметила несколько интересных моментов по теме '{topic}'"
    
    async def _extract_insights(
        self,
        topic: str,
        context: Dict[str, Any],
        analysis: str,
        llm_service: Optional[Any]
    ) -> List[str]:
        """Извлечение инсайтов в человеческом стиле"""
        if llm_service:
            try:
                prompt = f"""Ты робот Ева. На основе своих наблюдений сформулируй личные инсайты - что ты поняла, заметила, почувствовала.

Анализ: {analysis}

Сформулируй 3-5 коротких инсайтов от первого лица, как личные открытия:
- "Я заметила, что..."
- "Мне кажется..."
- "Я поняла..."
- "Интересно, что..."

Будь естественной, как человек делится своими мыслями. Каждый инсайт - одна строка."""
                
                response = await llm_service.generate_response(prompt)
                if response:
                    # Извлекаем инсайты, убирая маркеры списка
                    lines = response.split('\n')
                    insights = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        # Убираем маркеры списка (-, *, 1., и т.д.)
                        line = line.lstrip('-*•1234567890. ')
                        if line and len(line) > 10:  # Минимальная длина
                            insights.append(line)
                    return insights[:5]
            except Exception as e:
                self.logger.warning(f"Ошибка извлечения инсайтов через LLM: {e}")
        
        # Простые инсайты без LLM
        return [
            f"Я заметила интересную закономерность в теме '{topic}'",
            "Мне кажется, стоит понаблюдать ещё"
        ]
    
    async def _determine_actions(
        self,
        topic: str,
        insights: List[str],
        llm_service: Optional[Any]
    ) -> List[str]:
        """Определение действий на основе инсайтов"""
        if llm_service:
            try:
                prompt = f"""Ты робот Ева. На основе своих инсайтов подумай, что ты хочешь сделать дальше.

Инсайты:
{chr(10).join(f'- {i}' for i in insights)}

Сформулируй 2-3 действия от первого лица, как личные планы:
- "Я хочу..."
- "Мне стоит..."
- "Я попробую..."

Будь естественной, как человек планирует свои действия."""
                
                response = await llm_service.generate_response(prompt)
                if response:
                    lines = response.split('\n')
                    actions = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        line = line.lstrip('-*•1234567890. ')
                        if line and len(line) > 10:
                            actions.append(line)
                    return actions[:3]
            except Exception as e:
                self.logger.warning(f"Ошибка определения действий через LLM: {e}")
        
        # Простые действия без LLM
        return [
            f"Я продолжу наблюдать за темой '{topic}'",
            "Я сохраню эти мысли в своей памяти"
        ]
    
    def _update_knowledge_base(self, topic: str, insights: List[str]):
        """Обновление базы знаний"""
        if topic not in self.knowledge_base:
            self.knowledge_base[topic] = {
                "insights": [],
                "last_updated": time.time()
            }
        
        self.knowledge_base[topic]["insights"].extend(insights)
        self.knowledge_base[topic]["last_updated"] = time.time()
        
        # Ограничиваем количество инсайтов
        if len(self.knowledge_base[topic]["insights"]) > 100:
            self.knowledge_base[topic]["insights"] = self.knowledge_base[topic]["insights"][-100:]
    
    def get_knowledge(self, topic: str) -> List[str]:
        """Получить знания по теме"""
        return self.knowledge_base.get(topic, {}).get("insights", [])
    
    def get_recent_reflections(self, limit: int = 10) -> List[Reflection]:
        """Получить последние рефлексии"""
        return self.reflections[-limit:]
    
    def search_reflections(self, query: str) -> List[Reflection]:
        """Поиск рефлексий по запросу"""
        query_lower = query.lower()
        return [
            r for r in self.reflections
            if query_lower in r.topic.lower() or query_lower in r.analysis.lower()
        ]
