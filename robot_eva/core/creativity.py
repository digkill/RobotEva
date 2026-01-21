"""
Система креативности - генерация идей и решений
"""
import logging
import time
import json
import os
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import asyncio


@dataclass
class CreativeIdea:
    """Креативная идея"""
    id: str
    timestamp: float
    category: str  # "story", "solution", "improvement", "art", "joke", etc.
    prompt: str
    content: str
    quality_score: float  # 0.0 - 1.0
    originality: float    # 0.0 - 1.0
    usefulness: float     # 0.0 - 1.0
    tags: List[str]
    context: Dict[str, Any]


@dataclass
class CreativeSession:
    """Сессия креативности"""
    id: str
    timestamp: float
    goal: str
    ideas_generated: int
    best_idea: Optional[str]
    duration: float
    techniques_used: List[str]
    outcome: str


class CreativitySystem:
    """
    Система креативности

    Позволяет роботу:
    - Генерировать креативные идеи
    - Создавать истории и шутки
    - Находить нестандартные решения
    - Развивать творческие способности
    """

    def __init__(self, config, consciousness_ref=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.consciousness = consciousness_ref

        # База идей
        self.ideas: Dict[str, CreativeIdea] = {}
        self.sessions: List[CreativeSession] = []

        # Статистика
        self.stats = {
            "total_ideas": 0,
            "categories_used": defaultdict(int),
            "avg_quality": 0.0,
            "avg_originality": 0.0,
            "successful_sessions": 0
        }

        # Пути к данным
        self.data_path = "/home/pi/Projects/RobotEva/data/creativity"
        self.ideas_file = os.path.join(self.data_path, "ideas.json")
        self.sessions_file = os.path.join(self.data_path, "sessions.json")

        # Настройки
        self.max_ideas = 1000
        self.max_sessions = 100
        self.quality_threshold = 0.6

        # Техники креативности
        self.techniques = {
            "brainstorming": self._brainstorming,
            "lateral_thinking": self._lateral_thinking,
            "metaphorical": self._metaphorical,
            "provocative": self._provocative,
            "wishful_thinking": self._wishful_thinking,
            "random_associations": self._random_associations
        }

        # Темы для генерации
        self.themes = {
            "stories": [
                "приключение робота", "любовь ИИ", "будущее технологий",
                "дружба человека и машины", "путешествие во времени",
                "параллельные миры", "супергерой-робот"
            ],
            "solutions": [
                "решение экологических проблем", "улучшение образования",
                "борьба с одиночеством", "развитие искусственного интеллекта",
                "помощь пожилым людям", "сохранение природы"
            ],
            "jokes": [
                "шутки про роботов", "технологические шутки",
                "программистский юмор", "научный юмор"
            ],
            "improvements": [
                "улучшение интерфейсов", "новые способы общения",
                "инновации в образовании", "креативные гаджеты"
            ]
        }

        # Создаем директорию
        os.makedirs(self.data_path, exist_ok=True)

        # Загружаем данные
        self._load_data()

    async def initialize(self):
        """Инициализация системы креативности"""
        self.logger.info("Инициализация системы креативности")
        self.logger.info(f"Загружено {len(self.ideas)} идей, {len(self.sessions)} сессий")

    def _load_data(self):
        """Загрузка данных"""
        try:
            # Загружаем идеи
            if os.path.exists(self.ideas_file):
                with open(self.ideas_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for idea_id, idea_data in data.get("ideas", {}).items():
                        idea = CreativeIdea(**idea_data)
                        self.ideas[idea_id] = idea

            # Загружаем сессии
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = [CreativeSession(**session) for session in data.get("sessions", [])]

        except Exception as e:
            self.logger.warning(f"Ошибка загрузки данных креативности: {e}")

    def save_data(self):
        """Сохранение данных"""
        try:
            # Сохраняем идеи
            all_items = list(self.ideas.items())
            recent_items = all_items[-self.max_ideas:] if len(all_items) > self.max_ideas else all_items
            ideas_data = {
                "ideas": {idea_id: asdict(idea) for idea_id, idea in recent_items},
                "saved_at": time.time()
            }
            with open(self.ideas_file, 'w', encoding='utf-8') as f:
                json.dump(ideas_data, f, indent=2, ensure_ascii=False)

            # Сохраняем сессии
            sessions_data = {
                "sessions": [asdict(session) for session in self.sessions[-self.max_sessions:]],
                "saved_at": time.time()
            }
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных креативности: {e}")

    async def generate_idea(self, category: str, prompt: str = "",
                          technique: str = "auto", context: Dict = None) -> Optional[CreativeIdea]:
        """
        Сгенерировать креативную идею

        Args:
            category: Категория идеи
            prompt: Промпт для генерации
            technique: Техника креативности
            context: Контекст

        Returns:
            Сгенерированная идея или None
        """
        if not self.consciousness or not hasattr(self.consciousness, 'llm_service'):
            return None

        if context is None:
            context = {}

        llm = self.consciousness.llm_service

        try:
            # Выбираем технику
            if technique == "auto":
                technique = random.choice(list(self.techniques.keys()))

            # Генерируем промпт
            full_prompt = self._build_prompt(category, prompt, technique, context)

            # Генерируем идею
            idea_content = await llm.generate_response(full_prompt, max_tokens=500)

            if not idea_content:
                return None

            # Оцениваем идею
            quality_score = await self._evaluate_idea(idea_content, category, llm)
            originality, usefulness = await self._assess_idea_quality(idea_content, category)

            # Создаем идею
            idea_id = f"idea_{int(time.time())}_{random.randint(1000, 9999)}"

            idea = CreativeIdea(
                id=idea_id,
                timestamp=time.time(),
                category=category,
                prompt=prompt or full_prompt,
                content=idea_content,
                quality_score=quality_score,
                originality=originality,
                usefulness=usefulness,
                tags=self._extract_tags(idea_content),
                context=context
            )

            # Сохраняем
            self.ideas[idea.id] = idea
            self.stats["total_ideas"] += 1
            self.stats["categories_used"][category] += 1

            # Обновляем статистику
            self._update_stats()

            self.save_data()

            self.logger.info(f"Сгенерирована идея: {category} (качество: {quality_score:.2f})")
            return idea

        except Exception as e:
            self.logger.error(f"Ошибка генерации идеи: {e}")
            return None

    def _build_prompt(self, category: str, prompt: str, technique: str, context: Dict) -> str:
        """Построить промпт для генерации идеи"""
        base_prompts = {
            "story": "Напиши короткую креативную историю",
            "solution": "Предложи оригинальное решение проблемы",
            "joke": "Придумай смешную шутку",
            "improvement": "Предложи инновационное улучшение",
            "art": "Опиши художественное произведение",
            "poem": "Напиши стихотворение"
        }

        technique_descriptions = {
            "brainstorming": "Используй технику мозгового штурма - генерируй много идей",
            "lateral_thinking": "Применяй lateral thinking - нестандартные ассоциации",
            "metaphorical": "Используй метафоры и аналогии",
            "provocative": "Будь провокационным и нестандартным",
            "wishful_thinking": "Представь идеальный мир и решения в нем",
            "random_associations": "Связывай случайные понятия"
        }

        parts = []

        # Базовый промпт
        base = base_prompts.get(category, f"Создай креативный контент в категории {category}")
        parts.append(base)

        # Техника
        if technique in technique_descriptions:
            parts.append(f"Техника: {technique_descriptions[technique]}")

        # Пользовательский промпт
        if prompt:
            parts.append(f"Тема/запрос: {prompt}")

        # Контекст
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            parts.append(f"Контекст: {context_str}")

        # Инструкции по креативности
        parts.append("""
Будь максимально креативным и оригинальным!
- Не используй банальные решения
- Ищи неожиданные связи
- Добавляй юмор или глубокий смысл
- Будь конкретным и детализированным
        """.strip())

        return "\n\n".join(parts)

    async def _evaluate_idea(self, idea_content: str, category: str, llm) -> float:
        """Оценить качество идеи"""
        try:
            eval_prompt = f"""
Оцени креативность этой идеи по шкале 0.0-1.0:

Категория: {category}
Идея: {idea_content}

Критерии оценки:
- Оригинальность (новизна подхода)
- Качество исполнения
- Потенциальная полезность
- Креативность решения

Верни только число от 0.0 до 1.0
"""

            response = await llm.generate_response(eval_prompt, max_tokens=50)
            if response:
                try:
                    score = float(response.strip())
                    return max(0.0, min(1.0, score))
                except ValueError:
                    pass

        except Exception as e:
            self.logger.warning(f"Ошибка оценки идеи: {e}")

        return 0.5  # Средняя оценка по умолчанию

    async def _assess_idea_quality(self, idea_content: str, category: str) -> Tuple[float, float]:
        """Оценить оригинальность и полезность идеи"""
        # Простая эвристическая оценка
        originality = 0.5
        usefulness = 0.5

        # Оригинальность - проверяем на наличие нестандартных слов/идей
        original_words = ["неожиданно", "парадокс", "революция", "инновация",
                         "трансформация", "эволюция", "прорыв", "гениально"]
        if any(word in idea_content.lower() for word in original_words):
            originality += 0.3

        # Длина и детализация
        if len(idea_content) > 200:
            originality += 0.1
            usefulness += 0.1

        # Категорийные особенности
        if category == "solution" and ("решение" in idea_content or "способ" in idea_content):
            usefulness += 0.2
        elif category == "joke" and ("смех" in idea_content or any(word in idea_content.lower()
                for word in ["ха", "хи", "хе", "хох", "хах"])):
            usefulness += 0.3

        return min(1.0, originality), min(1.0, usefulness)

    def _extract_tags(self, content: str) -> List[str]:
        """Извлечь теги из контента"""
        tags = []

        # Ключевые слова для тегов
        tag_keywords = {
            "технологии": ["технолог", "цифр", "компьютер", "робот", "ии", "ai"],
            "творчество": ["творч", "креатив", "искусств", "худож"],
            "юмор": ["шутк", "смешн", "юмор", "прикол"],
            "наука": ["науч", "исследов", "эксперим", "открыт"],
            "будущее": ["будущ", "завтра", "грядущ"],
            "человек": ["человеч", "люд", "обществ"],
            "природа": ["природ", "эколог", "планет", "земл"]
        }

        content_lower = content.lower()
        for tag, keywords in tag_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                tags.append(tag)

        return tags[:5]  # Максимум 5 тегов

    def _update_stats(self):
        """Обновить статистику"""
        if self.ideas:
            qualities = [idea.quality_score for idea in self.ideas.values()]
            originalities = [idea.originality for idea in self.ideas.values()]

            self.stats["avg_quality"] = sum(qualities) / len(qualities)
            self.stats["avg_originality"] = sum(originalities) / len(originalities)

    async def start_creative_session(self, goal: str, duration_minutes: int = 10) -> str:
        """
        Начать креативную сессию

        Args:
            goal: Цель сессии
            duration_minutes: Длительность в минутах

        Returns:
            ID сессии
        """
        session_id = f"session_{int(time.time())}"

        session = CreativeSession(
            id=session_id,
            timestamp=time.time(),
            goal=goal,
            ideas_generated=0,
            best_idea=None,
            duration=duration_minutes * 60,
            techniques_used=[],
            outcome="in_progress"
        )

        self.sessions.append(session)

        # Запускаем сессию
        asyncio.create_task(self._run_creative_session(session))

        self.logger.info(f"Начата креативная сессия: {goal}")
        return session_id

    async def _run_creative_session(self, session: CreativeSession):
        """Выполнить креативную сессию"""
        try:
            start_time = time.time()
            ideas = []

            # Выбираем техники
            techniques = random.sample(list(self.techniques.keys()), 3)

            for technique in techniques:
                # Генерируем идею
                idea = await self.generate_idea(
                    category=self._choose_category_for_goal(session.goal),
                    prompt=session.goal,
                    technique=technique,
                    context={"session_goal": session.goal}
                )

                if idea:
                    ideas.append(idea)
                    session.techniques_used.append(technique)
                    session.ideas_generated += 1

                # Небольшая пауза
                await asyncio.sleep(2)

            # Выбираем лучшую идею
            if ideas:
                best_idea = max(ideas, key=lambda x: x.quality_score)
                session.best_idea = best_idea.id

            session.outcome = "completed"
            session.duration = time.time() - start_time

            # Обновляем статистику
            if session.ideas_generated > 0:
                self.stats["successful_sessions"] += 1

            self.save_data()

            self.logger.info(f"Завершена креативная сессия: {session.ideas_generated} идей")

        except Exception as e:
            session.outcome = "failed"
            self.logger.error(f"Ошибка в креативной сессии: {e}")

    def _choose_category_for_goal(self, goal: str) -> str:
        """Выбрать категорию на основе цели"""
        goal_lower = goal.lower()

        if any(word in goal_lower for word in ["история", "рассказ", "повесть"]):
            return "story"
        elif any(word in goal_lower for word in ["решение", "проблема", "задача"]):
            return "solution"
        elif any(word in goal_lower for word in ["шутка", "юмор", "смех"]):
            return "joke"
        elif any(word in goal_lower for word in ["улучшение", "оптимизация", "развитие"]):
            return "improvement"
        elif any(word in goal_lower for word in ["стихи", "поэзия", "стихотворение"]):
            return "poem"
        else:
            return random.choice(list(self.themes.keys()))

    async def tell_story(self, theme: str = "") -> Optional[str]:
        """Рассказать историю"""
        if not theme:
            theme = random.choice(self.themes["stories"])

        idea = await self.generate_idea("story", f"История на тему: {theme}")
        return idea.content if idea else None

    async def make_joke(self, topic: str = "") -> Optional[str]:
        """Придумать шутку"""
        prompt = f"Шутка на тему: {topic}" if topic else "Смешная шутка"
        idea = await self.generate_idea("joke", prompt)
        return idea.content if idea else None

    async def solve_problem(self, problem: str) -> Optional[str]:
        """Предложить решение проблемы"""
        idea = await self.generate_idea("solution", f"Решение проблемы: {problem}")
        return idea.content if idea else None

    async def get_random_inspiration(self) -> Optional[str]:
        """Получить случайное вдохновение"""
        category = random.choice(list(self.themes.keys()))
        theme = random.choice(self.themes[category])

        idea = await self.generate_idea(category, f"Вдохновляющая идея: {theme}")
        return idea.content if idea else None

    # Техники креативности
    async def _brainstorming(self, category: str, prompt: str, context: Dict) -> str:
        """Техника мозгового штурма"""
        base = f"Мозговой штурм для категории '{category}': {prompt}\n\n"
        base += "Сгенерируй как можно больше идей:\n"
        return base + "Идея должна быть креативной и нестандартной."

    async def _lateral_thinking(self, category: str, prompt: str, context: Dict) -> str:
        """Латеральное мышление"""
        base = f"Латеральное мышление для '{category}': {prompt}\n\n"
        base += "Ищи неожиданные связи и ассоциации:\n"
        return base + "Подумай о проблеме с совершенно другой стороны."

    async def _metaphorical(self, category: str, prompt: str, context: Dict) -> str:
        """Метафорический подход"""
        base = f"Метафора для '{category}': {prompt}\n\n"
        base += "Используй аналогии и образы:\n"
        return base + "Если бы это была метафора, то как бы она звучала?"

    async def _provocative(self, category: str, prompt: str, context: Dict) -> str:
        """Провокационный подход"""
        base = f"Провокационная идея для '{category}': {prompt}\n\n"
        base += "Будь смелым и нестандартным:\n"
        return base + "Даже если идея шокирующая - это нормально для креативности!"

    async def _wishful_thinking(self, category: str, prompt: str, context: Dict) -> str:
        """Мечтательное мышление"""
        base = f"Идеальный мир для '{category}': {prompt}\n\n"
        base += "Представь идеальное решение:\n"
        return base + "Если бы не было ограничений, как бы это выглядело?"

    async def _random_associations(self, category: str, prompt: str, context: Dict) -> str:
        """Случайные ассоциации"""
        words = ["кот", "облако", "велосипед", "звезда", "море", "книга", "танец"]
        random_word = random.choice(words)
        base = f"Связь '{random_word}' с '{category}': {prompt}\n\n"
        base += f"Как связаны {random_word} и твоя тема?\n"
        return base + "Найди неожиданную связь!"

    def get_creativity_stats(self) -> Dict[str, Any]:
        """Получить статистику креативности"""
        return {
            "total_ideas": self.stats["total_ideas"],
            "categories": dict(self.stats["categories_used"]),
            "avg_quality": self.stats["avg_quality"],
            "avg_originality": self.stats["avg_originality"],
            "successful_sessions": self.stats["successful_sessions"],
            "total_sessions": len(self.sessions)
        }

    def get_best_ideas(self, category: str = None, limit: int = 5) -> List[CreativeIdea]:
        """Получить лучшие идеи"""
        ideas = list(self.ideas.values())

        if category:
            ideas = [idea for idea in ideas if idea.category == category]

        # Сортируем по качеству
        ideas.sort(key=lambda x: x.quality_score, reverse=True)

        return ideas[:limit]

    def search_ideas(self, query: str, category: str = None) -> List[CreativeIdea]:
        """Поиск идей"""
        results = []

        for idea in self.ideas.values():
            if category and idea.category != category:
                continue

            # Поиск по контенту и тегам
            search_text = f"{idea.content} {' '.join(idea.tags)} {idea.category}".lower()

            if query.lower() in search_text:
                results.append(idea)

        # Сортируем по релевантности (простая версия)
        return results[:10]