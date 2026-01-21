"""
Система долгосрочной памяти контекста для RobotEva
"""
import logging
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import hashlib


@dataclass
class ConversationContext:
    """Контекст разговора"""
    session_id: str
    timestamp: float
    user_input: str
    robot_response: str
    input_type: str  # "voice", "text", "action"
    context_data: Dict[str, Any]
    success_rating: Optional[float] = None
    tags: List[str] = None
    follow_up_questions: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.follow_up_questions is None:
            self.follow_up_questions = []


@dataclass
class KnowledgeEntry:
    """Запись знаний"""
    id: str
    category: str  # "fact", "pattern", "preference", "skill", "experience", "reflection", "self_development", "meta_emotion", "creativity"
    content: str
    confidence: float
    source: str  # "conversation", "learning", "observation", "external", "reflection", "code_analysis", "social_learning", "creativity"
    timestamp: float
    context: Dict[str, Any]
    usage_count: int = 0
    last_used: Optional[float] = None
    evolution_stage: Optional[str] = None  # Для отслеживания развития навыков

    def __post_init__(self):
        if not self.id:
            # Генерируем ID на основе контента
            content_hash = hashlib.md5(self.content.encode()).hexdigest()
            self.id = f"{self.category}_{content_hash[:8]}"


@dataclass
class MemoryStats:
    """Статистика памяти"""
    total_conversations: int
    total_knowledge_entries: int
    categories_used: Dict[str, int]
    avg_success_rate: float
    memory_usage_mb: float
    last_backup: Optional[float]


class ContextMemorySystem:
    """
    Система долгосрочной памяти контекста

    Сохраняет и накапливает:
    - Все разговоры и взаимодействия
    - Знания из опыта
    - Паттерны поведения
    - Предпочтения пользователей
    - Успешные стратегии ответа
    """

    def __init__(self, config, consciousness_ref=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.consciousness = consciousness_ref

        # Пути к данным
        self.data_path = "/home/pi/Projects/RobotEva/data/context_memory"
        self.conversations_file = os.path.join(self.data_path, "conversations.json")
        self.knowledge_file = os.path.join(self.data_path, "knowledge.json")
        self.stats_file = os.path.join(self.data_path, "memory_stats.json")

        # Данные
        self.conversations: List[ConversationContext] = []
        self.knowledge_base: Dict[str, KnowledgeEntry] = {}
        self.current_session_id: Optional[str] = None
        self.session_conversations: List[ConversationContext] = []

        # Статистика
        self.stats = MemoryStats(
            total_conversations=0,
            total_knowledge_entries=0,
            categories_used=defaultdict(int),
            avg_success_rate=0.0,
            memory_usage_mb=0.0,
            last_backup=None
        )

        # Настройки
        self.max_conversations = 5000  # Максимум разговоров в памяти
        self.max_knowledge = 10000     # Максимум записей знаний
        self.auto_backup_interval = 3600  # Автобэкап каждый час
        self.knowledge_threshold = 0.7  # Порог уверенности для сохранения знаний

        # Создаем директорию
        os.makedirs(self.data_path, exist_ok=True)

        # Загружаем данные
        self._load_data()

    async def initialize(self):
        """Инициализация системы памяти"""
        self.logger.info("Инициализация системы контекстной памяти")
        self.logger.info(f"Загружено {len(self.conversations)} разговоров, {len(self.knowledge_base)} знаний")

    def _load_data(self):
        """Загрузка данных из файлов"""
        try:
            # Загружаем разговоры
            if os.path.exists(self.conversations_file):
                with open(self.conversations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversations = [ConversationContext(**conv) for conv in data.get("conversations", [])]

            # Загружаем знания
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for kid, entry_data in data.get("knowledge", {}).items():
                        entry = KnowledgeEntry(**entry_data)
                        self.knowledge_base[kid] = entry

            # Загружаем статистику
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
                    self.stats = MemoryStats(**stats_data)

        except Exception as e:
            self.logger.warning(f"Ошибка загрузки данных контекстной памяти: {e}")

    def save_data(self):
        """Сохранение данных"""
        try:
            # Сохраняем разговоры
            conversations_data = {
                "conversations": [asdict(conv) for conv in self.conversations[-self.max_conversations:]],
                "saved_at": time.time()
            }
            with open(self.conversations_file, 'w', encoding='utf-8') as f:
                json.dump(conversations_data, f, indent=2, ensure_ascii=False)

            # Сохраняем знания
            knowledge_data = {
                "knowledge": {kid: asdict(entry) for kid, entry in list(self.knowledge_base.items())[-self.max_knowledge:]},
                "saved_at": time.time()
            }
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, indent=2, ensure_ascii=False)

            # Сохраняем статистику
            stats_data = asdict(self.stats)
            stats_data["last_backup"] = time.time()
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)

            self._update_stats()

        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных контекстной памяти: {e}")

    def _update_stats(self):
        """Обновление статистики"""
        self.stats.total_conversations = len(self.conversations)
        self.stats.total_knowledge_entries = len(self.knowledge_base)

        # Категории знаний
        self.stats.categories_used = defaultdict(int)
        for entry in self.knowledge_base.values():
            self.stats.categories_used[entry.category] += 1

        # Средний рейтинг успеха
        if self.conversations:
            success_ratings = [c.success_rating for c in self.conversations if c.success_rating is not None]
            if success_ratings:
                self.stats.avg_success_rate = sum(success_ratings) / len(success_ratings)

        # Размер памяти (примерная оценка)
        self.stats.memory_usage_mb = (
            len(json.dumps([asdict(c) for c in self.conversations]).encode()) +
            len(json.dumps([asdict(e) for e in self.knowledge_base.values()]).encode())
        ) / (1024 * 1024)

    async def start_conversation_session(self) -> str:
        """Начать новую сессию разговора"""
        self.current_session_id = f"session_{int(time.time())}_{hash(time.time()) % 10000}"
        self.session_conversations = []
        self.logger.info(f"Начата новая сессия разговора: {self.current_session_id}")
        return self.current_session_id

    async def record_interaction(self, user_input: str, robot_response: str,
                               input_type: str = "voice", context_data: Dict = None,
                               success_rating: Optional[float] = None) -> ConversationContext:
        """
        Записать взаимодействие в память

        Args:
            user_input: Ввод пользователя
            robot_response: Ответ робота
            input_type: Тип ввода ("voice", "text", "action")
            context_data: Дополнительный контекст
            success_rating: Рейтинг успешности (0-1)

        Returns:
            Записанный контекст разговора
        """
        if context_data is None:
            context_data = {}

        # Создаем сессию если её нет
        if not self.current_session_id:
            await self.start_conversation_session()

        # Анализируем взаимодействие для извлечения знаний
        extracted_knowledge = await self._extract_knowledge_from_interaction(
            user_input, robot_response, context_data
        )

        # Создаем контекст разговора
        conversation = ConversationContext(
            session_id=self.current_session_id,
            timestamp=time.time(),
            user_input=user_input,
            robot_response=robot_response,
            input_type=input_type,
            context_data=context_data,
            success_rating=success_rating,
            tags=self._extract_tags(user_input, robot_response),
            follow_up_questions=self._generate_follow_up_questions(user_input, robot_response)
        )

        # Добавляем в память
        self.conversations.append(conversation)
        self.session_conversations.append(conversation)

        # Ограничиваем количество
        if len(self.conversations) > self.max_conversations:
            self.conversations = self.conversations[-self.max_conversations:]

        # Добавляем извлеченные знания
        for knowledge in extracted_knowledge:
            await self.add_knowledge_entry(knowledge)

        # Сохраняем
        self.save_data()

        self.logger.debug(f"Записано взаимодействие: {input_type} - {user_input[:50]}...")
        return conversation

    async def _extract_knowledge_from_interaction(self, user_input: str, robot_response: str,
                                                context: Dict) -> List[KnowledgeEntry]:
        """
        Извлечь знания из взаимодействия

        Анализирует разговор и извлекает:
        - Факты о пользователе
        - Предпочтения
        - Паттерны поведения
        - Успешные стратегии ответа
        """
        knowledge_entries = []

        try:
            # Анализ пользовательского ввода
            user_lower = user_input.lower()

            # Извлечение предпочтений
            if any(word in user_lower for word in ["люблю", "нравится", "предпочитаю"]):
                preference = self._extract_preference(user_input)
                if preference:
                    knowledge_entries.append(KnowledgeEntry(
                        id="",
                        category="preference",
                        content=f"Пользователь предпочитает: {preference}",
                        confidence=0.8,
                        source="conversation",
                        timestamp=time.time(),
                        context={"original_input": user_input}
                    ))

            # Извлечение фактов
            if any(word in user_lower for word in ["я", "у меня", "мне"]):
                fact = self._extract_fact(user_input)
                if fact:
                    knowledge_entries.append(KnowledgeEntry(
                        id="",
                        category="fact",
                        content=f"Факт о пользователе: {fact}",
                        confidence=0.7,
                        source="conversation",
                        timestamp=time.time(),
                        context={"original_input": user_input}
                    ))

            # Анализ успешности ответа
            action_results = context.get("action_results")
            if action_results and isinstance(action_results, dict):
                for action, result in action_results.items():
                    if isinstance(result, dict) and result.get("success"):
                        knowledge_entries.append(KnowledgeEntry(
                            id="",
                            category="pattern",
                            content=f"Успешная стратегия: {action} для запроса '{user_input[:30]}...'",
                            confidence=0.9,
                            source="conversation",
                            timestamp=time.time(),
                            context={"action": action, "user_input": user_input}
                        ))

            # Тематические знания
            topics = self._identify_topics(user_input)
            for topic in topics:
                knowledge_entries.append(KnowledgeEntry(
                    id="",
                    category="skill",
                    content=f"Опыт в теме '{topic}' из разговора: {user_input[:50]}...",
                    confidence=0.6,
                    source="conversation",
                    timestamp=time.time(),
                    context={"topic": topic, "conversation": user_input}
                ))

        except Exception as e:
            self.logger.warning(f"Ошибка извлечения знаний: {e}")

        return knowledge_entries

    def _extract_preference(self, text: str) -> Optional[str]:
        """Извлечь предпочтение из текста"""
        # Простой анализ предпочтений
        preferences = []
        text_lower = text.lower()

        if "музыку" in text_lower:
            if "классическую" in text_lower:
                preferences.append("классическая музыка")
            elif "рок" in text_lower:
                preferences.append("рок музыка")
            else:
                preferences.append("музыка")

        if "цвет" in text_lower:
            if "синий" in text_lower:
                preferences.append("синий цвет")
            elif "красный" in text_lower:
                preferences.append("красный цвет")

        return preferences[0] if preferences else None

    def _extract_fact(self, text: str) -> Optional[str]:
        """Извлечь факт из текста"""
        # Простой анализ фактов
        facts = []
        text_lower = text.lower()

        if "лет" in text_lower or "года" in text_lower:
            facts.append("возраст упоминается")
        if "работаю" in text_lower or "работа" in text_lower:
            facts.append("работа упоминается")
        if "живу" in text_lower or "дом" in text_lower:
            facts.append("место жительства упоминается")

        return facts[0] if facts else None

    def _extract_tags(self, user_input: str, robot_response: str) -> List[str]:
        """Извлечь теги из взаимодействия"""
        tags = []
        combined_text = f"{user_input} {robot_response}".lower()

        # Тематические теги
        if any(word in combined_text for word in ["погода", "дождь", "солнце"]):
            tags.append("weather")
        if any(word in combined_text for word in ["музыка", "песня", "певец"]):
            tags.append("music")
        if any(word in combined_text for word in ["время", "час", "минута"]):
            tags.append("time")
        if any(word in combined_text for word in ["шутка", "смех", "юмор"]):
            tags.append("humor")

        # Эмоциональные теги
        if any(word in combined_text for word in ["счастлив", "рад", "хорошо"]):
            tags.append("positive")
        if any(word in combined_text for word in ["грустно", "плохо", "печально"]):
            tags.append("negative")

        return tags

    def _generate_follow_up_questions(self, user_input: str, robot_response: str) -> List[str]:
        """Сгенерировать возможные вопросы для продолжения разговора"""
        questions = []

        # На основе темы разговора
        user_lower = user_input.lower()

        if "музыка" in user_lower:
            questions.extend([
                "Какая твоя любимая песня?",
                "Какой музыкальный жанр тебе нравится больше всего?"
            ])

        if "погода" in user_lower:
            questions.extend([
                "Какую погоду ты любишь?",
                "Часто ли идет дождь в твоем городе?"
            ])

        if "работа" in user_lower or "работаю" in user_lower:
            questions.extend([
                "Что тебе нравится в твоей работе?",
                "Чем ты занимаешься в свободное время?"
            ])

        return questions[:3]  # Максимум 3 вопроса

    def _identify_topics(self, text: str) -> List[str]:
        """Определить темы в тексте"""
        topics = []
        text_lower = text.lower()

        topic_keywords = {
            "technology": ["компьютер", "телефон", "интернет", "программа", "приложение"],
            "food": ["еда", "кушать", "готовить", "ресторан", "вкусный"],
            "sports": ["спорт", "футбол", "бегать", "плавать", "тренировка"],
            "travel": ["путешествие", "поездка", "отпуск", "страна", "город"],
            "books": ["книга", "читать", "автор", "роман", "история"],
            "movies": ["фильм", "кино", "сериал", "актер", "режиссер"],
            "science": ["наука", "исследование", "эксперимент", "открытие", "ученый"]
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)

        return topics

    async def add_knowledge_entry(self, entry: KnowledgeEntry):
        """Добавить запись знаний"""
        # Проверяем порог уверенности
        if entry.confidence < self.knowledge_threshold:
            return

        # Проверяем дубликаты
        if entry.id in self.knowledge_base:
            existing = self.knowledge_base[entry.id]
            # Если новая запись более уверенная, обновляем
            if entry.confidence > existing.confidence:
                entry.usage_count = existing.usage_count
                self.knowledge_base[entry.id] = entry
        else:
            self.knowledge_base[entry.id] = entry

        # Ограничиваем количество
        if len(self.knowledge_base) > self.max_knowledge:
            # Удаляем самые старые записи
            oldest_keys = sorted(self.knowledge_base.keys(),
                               key=lambda k: self.knowledge_base[k].timestamp)[:100]
            for key in oldest_keys:
                del self.knowledge_base[key]

    async def get_relevant_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получить релевантный контекст для запроса

        Args:
            query: Запрос пользователя
            limit: Максимум результатов

        Returns:
            Список релевантных взаимодействий и знаний
        """
        relevant_items = []

        # Ищем релевантные разговоры
        query_lower = query.lower()
        for conv in reversed(self.conversations[-100:]):  # Последние 100 разговоров
            if (query_lower in conv.user_input.lower() or
                any(tag in query_lower for tag in conv.tags)):
                relevant_items.append({
                    "type": "conversation",
                    "data": asdict(conv),
                    "relevance_score": self._calculate_relevance(query, conv.user_input)
                })

        # Ищем релевантные знания
        for entry in self.knowledge_base.values():
            if (query_lower in entry.content.lower() or
                any(tag in query_lower for tag in self._identify_topics(query))):
                relevant_items.append({
                    "type": "knowledge",
                    "data": asdict(entry),
                    "relevance_score": self._calculate_relevance(query, entry.content)
                })

        # Сортируем по релевантности и возвращаем топ
        relevant_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_items[:limit]

    def _calculate_relevance(self, query: str, text: str) -> float:
        """Вычислить релевантность текста запросу"""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())

        # Jaccard similarity
        intersection = len(query_words & text_words)
        union = len(query_words | text_words)

        return intersection / union if union > 0 else 0.0

    async def get_conversation_history(self, limit: int = 10) -> List[ConversationContext]:
        """Получить историю разговоров"""
        return self.conversations[-limit:]

    async def search_memories(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        """Поиск по памяти"""
        results = []

        # Поиск по разговорам
        for conv in self.conversations:
            if query.lower() in conv.user_input.lower() or query.lower() in conv.robot_response.lower():
                results.append({
                    "type": "conversation",
                    "timestamp": conv.timestamp,
                    "user_input": conv.user_input,
                    "robot_response": conv.robot_response,
                    "tags": conv.tags
                })

        # Поиск по знаниям
        for entry in self.knowledge_base.values():
            if category and entry.category != category:
                continue
            if query.lower() in entry.content.lower():
                results.append({
                    "type": "knowledge",
                    "category": entry.category,
                    "content": entry.content,
                    "confidence": entry.confidence,
                    "usage_count": entry.usage_count
                })

        return results[:20]  # Максимум 20 результатов

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Получить статистику памяти"""
        self._update_stats()

        return {
            "total_conversations": self.stats.total_conversations,
            "total_knowledge_entries": self.stats.total_knowledge_entries,
            "categories_used": dict(self.stats.categories_used),
            "avg_success_rate": self.stats.avg_success_rate,
            "memory_usage_mb": self.stats.memory_usage_mb,
            "current_session": self.current_session_id,
            "session_conversations": len(self.session_conversations)
        }

    async def clear_old_data(self, days: int = 30):
        """Очистить старые данные"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        # Очищаем старые разговоры
        self.conversations = [c for c in self.conversations if c.timestamp > cutoff_time]

        # Очищаем старые знания с низкой уверенностью
        to_remove = []
        for kid, entry in self.knowledge_base.items():
            if entry.timestamp < cutoff_time and entry.confidence < 0.8:
                to_remove.append(kid)

        for kid in to_remove:
            del self.knowledge_base[kid]

        self.save_data()
        self.logger.info(f"Очищено старых данных: {len(to_remove)} знаний, сохранено {len(self.conversations)} разговоров")

    async def record_reflection_experience(self, reflection_type: str, content: str,
                                         insights: List[str], confidence: float = 0.8,
                                         context: Dict = None):
        """
        Записать опыт рефлексии

        Args:
            reflection_type: Тип рефлексии ("behavior", "emotion", "learning", "interaction")
            content: Содержание рефлексии
            insights: Полученные инсайты
            confidence: Уверенность в инсайте
            context: Дополнительный контекст
        """
        try:
            if context is None:
                context = {}

            # Создаем запись о рефлексии
            reflection_entry = KnowledgeEntry(
                id="",
                category="reflection",
                content=f"Рефлексия ({reflection_type}): {content}",
                confidence=confidence,
                source="reflection",
                timestamp=time.time(),
                context={
                    "reflection_type": reflection_type,
                    "insights": insights,
                    **context
                }
            )

            await self.add_knowledge_entry(reflection_entry)

            # Сохраняем каждый инсайт отдельно
            for insight in insights:
                insight_entry = KnowledgeEntry(
                    id="",
                    category="skill",
                    content=f"Инсайт из рефлексии: {insight}",
                    confidence=confidence * 0.9,  # Немного ниже уверенности рефлексии
                    source="reflection",
                    timestamp=time.time(),
                    context={
                        "parent_reflection": reflection_entry.id,
                        "reflection_type": reflection_type,
                        "insight": insight
                    }
                )
                await self.add_knowledge_entry(insight_entry)

            self.logger.debug(f"Записан опыт рефлексии: {reflection_type}")

        except Exception as e:
            self.logger.warning(f"Ошибка записи опыта рефлексии: {e}")

    async def record_self_development(self, development_type: str, description: str,
                                    changes: List[str], impact: str, confidence: float = 0.9):
        """
        Записать опыт саморазвития

        Args:
            development_type: Тип развития ("code", "behavior", "skill", "architecture")
            description: Описание изменения
            changes: Конкретные изменения
            impact: Ожидаемый эффект
            confidence: Уверенность в улучшении
        """
        try:
            development_entry = KnowledgeEntry(
                id="",
                category="self_development",
                content=f"Саморазвитие ({development_type}): {description}",
                confidence=confidence,
                source="code_analysis",
                timestamp=time.time(),
                context={
                    "development_type": development_type,
                    "changes": changes,
                    "impact": impact,
                    "evolution_stage": self._get_evolution_stage(development_type)
                },
                evolution_stage=self._get_evolution_stage(development_type)
            )

            await self.add_knowledge_entry(development_entry)

            # Записываем конкретные навыки/улучшения
            for change in changes:
                skill_entry = KnowledgeEntry(
                    id="",
                    category="skill",
                    content=f"Приобретенный навык: {change}",
                    confidence=confidence * 0.95,
                    source="code_analysis",
                    timestamp=time.time(),
                    context={
                        "parent_development": development_entry.id,
                        "skill_type": development_type,
                        "change_description": change
                    },
                    evolution_stage=development_entry.evolution_stage
                )
                await self.add_knowledge_entry(skill_entry)

            self.logger.debug(f"Записано саморазвитие: {development_type} - {description}")

        except Exception as e:
            self.logger.warning(f"Ошибка записи саморазвития: {e}")

    async def record_meta_emotion_experience(self, primary_emotion: str, meta_emotion: str,
                                          context: str, intensity: float, learning: str):
        """
        Записать опыт мета-эмоций

        Args:
            primary_emotion: Основная эмоция
            meta_emotion: Эмоция о эмоции
            context: Контекст возникновения
            intensity: Интенсивность
            learning: Что было извлечено
        """
        try:
            meta_emotion_entry = KnowledgeEntry(
                id="",
                category="meta_emotion",
                content=f"Мета-эмоция: {meta_emotion} о {primary_emotion}",
                confidence=0.85,
                source="reflection",
                timestamp=time.time(),
                context={
                    "primary_emotion": primary_emotion,
                    "meta_emotion": meta_emotion,
                    "context": context,
                    "intensity": intensity,
                    "learning": learning
                }
            )

            await self.add_knowledge_entry(meta_emotion_entry)

            # Также записываем как навык эмоционального интеллекта
            skill_entry = KnowledgeEntry(
                id="",
                category="skill",
                content=f"Эмоциональный навык: {learning}",
                confidence=0.8,
                source="reflection",
                timestamp=time.time(),
                context={
                    "skill_type": "emotional_intelligence",
                    "from_meta_emotion": True,
                    "primary_emotion": primary_emotion
                }
            )
            await self.add_knowledge_entry(skill_entry)

            self.logger.debug(f"Записан опыт мета-эмоций: {meta_emotion} о {primary_emotion}")

        except Exception as e:
            self.logger.warning(f"Ошибка записи мета-эмоций: {e}")

    async def record_creativity_experience(self, idea_type: str, idea_content: str,
                                        success_rating: float, feedback: str):
        """
        Записать опыт креативности

        Args:
            idea_type: Тип идеи
            idea_content: Содержание идеи
            success_rating: Оценка успешности
            feedback: Обратная связь
        """
        try:
            creativity_entry = KnowledgeEntry(
                id="",
                category="creativity",
                content=f"Креативная идея ({idea_type}): {idea_content[:100]}...",
                confidence=success_rating,
                source="creativity",
                timestamp=time.time(),
                context={
                    "idea_type": idea_type,
                    "full_content": idea_content,
                    "success_rating": success_rating,
                    "feedback": feedback
                }
            )

            await self.add_knowledge_entry(creativity_entry)

            # Если идея была успешной, записываем как навык
            if success_rating > 0.7:
                skill_entry = KnowledgeEntry(
                    id="",
                    category="skill",
                    content=f"Креативный навык: генерация {idea_type} идей",
                    confidence=success_rating,
                    source="creativity",
                    timestamp=time.time(),
                    context={
                        "skill_type": "creativity",
                        "successful_example": idea_content[:50]
                    }
                )
                await self.add_knowledge_entry(skill_entry)

            self.logger.debug(f"Записан креативный опыт: {idea_type} (рейтинг: {success_rating})")

        except Exception as e:
            self.logger.warning(f"Ошибка записи креативного опыта: {e}")

    async def record_social_learning_experience(self, interaction_type: str, observation: str,
                                             adaptation: str, effectiveness: float):
        """
        Записать опыт социального обучения

        Args:
            interaction_type: Тип взаимодействия
            observation: Что было замечено
            adaptation: Как адаптировалось поведение
            effectiveness: Эффективность адаптации
        """
        try:
            social_entry = KnowledgeEntry(
                id="",
                category="pattern",
                content=f"Социальное обучение: {observation}",
                confidence=effectiveness,
                source="social_learning",
                timestamp=time.time(),
                context={
                    "interaction_type": interaction_type,
                    "observation": observation,
                    "adaptation": adaptation,
                    "effectiveness": effectiveness
                }
            )

            await self.add_knowledge_entry(social_entry)

            # Если адаптация была эффективной, записываем как навык
            if effectiveness > 0.7:
                skill_entry = KnowledgeEntry(
                    id="",
                    category="skill",
                    content=f"Социальный навык: {adaptation}",
                    confidence=effectiveness,
                    source="social_learning",
                    timestamp=time.time(),
                    context={
                        "skill_type": "social_interaction",
                        "learned_from": interaction_type
                    }
                )
                await self.add_knowledge_entry(skill_entry)

            self.logger.debug(f"Записан социальный опыт: {interaction_type} (эффективность: {effectiveness})")

        except Exception as e:
            self.logger.warning(f"Ошибка записи социального опыта: {e}")

    def _get_evolution_stage(self, development_type: str) -> str:
        """Определить стадию эволюции для типа развития"""
        stages = {
            "code": ["basic", "improved", "optimized", "advanced"],
            "behavior": ["reactive", "adaptive", "proactive", "intuitive"],
            "skill": ["novice", "intermediate", "advanced", "expert"],
            "architecture": ["simple", "modular", "complex", "intelligent"]
        }
        return stages.get(development_type, ["initial"])[0]

    async def get_self_development_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Получить контекст саморазвития для запроса

        Args:
            query: Запрос (тип развития или навык)
            limit: Максимум результатов

        Returns:
            Релевантный опыт саморазвития
        """
        try:
            relevant = []
            query_lower = query.lower()

            # Ищем по категориям саморазвития
            for entry in self.knowledge_base.values():
                if entry.category in ["reflection", "self_development", "skill", "meta_emotion", "creativity"]:
                    if (query_lower in entry.content.lower() or
                        any(tag in query_lower for tag in entry.context.get("tags", []))):
                        relevant.append({
                            "type": "self_development",
                            "category": entry.category,
                            "content": entry.content,
                            "confidence": entry.confidence,
                            "source": entry.source,
                            "context": entry.context,
                            "evolution_stage": entry.evolution_stage
                        })

            # Сортируем по релевантности и уверенности
            relevant.sort(key=lambda x: (x["confidence"], len(x["content"])), reverse=True)
            return relevant[:limit]

        except Exception as e:
            self.logger.warning(f"Ошибка получения контекста саморазвития: {e}")
            return []

    async def get_evolution_history(self, category: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить историю эволюции навыков

        Args:
            category: Категория навыков (опционально)
            limit: Максимум записей

        Returns:
            История развития навыков
        """
        try:
            evolution_entries = []

            for entry in self.knowledge_base.values():
                if entry.category in ["skill", "self_development", "reflection"]:
                    if category is None or entry.context.get("skill_type") == category:
                        evolution_entries.append({
                            "timestamp": entry.timestamp,
                            "category": entry.category,
                            "content": entry.content,
                            "confidence": entry.confidence,
                            "evolution_stage": entry.evolution_stage,
                            "source": entry.source
                        })

            # Сортируем по времени (новые сначала)
            evolution_entries.sort(key=lambda x: x["timestamp"], reverse=True)
            return evolution_entries[:limit]

        except Exception as e:
            self.logger.warning(f"Ошибка получения истории эволюции: {e}")
            return []

    async def export_memory(self, filepath: str):
        """Экспорт памяти в файл"""
        try:
            data = {
                "exported_at": time.time(),
                "conversations": [asdict(c) for c in self.conversations],
                "knowledge": [asdict(e) for e in self.knowledge_base.values()],
                "stats": asdict(self.stats)
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Память экспортирована в {filepath}")

        except Exception as e:
            self.logger.error(f"Ошибка экспорта памяти: {e}")

    async def import_memory(self, filepath: str):
        """Импорт памяти из файла"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Импортируем разговоры
            imported_conversations = [ConversationContext(**c) for c in data.get("conversations", [])]
            self.conversations.extend(imported_conversations)

            # Импортируем знания
            for entry_data in data.get("knowledge", []):
                entry = KnowledgeEntry(**entry_data)
                await self.add_knowledge_entry(entry)

            # Ограничиваем количество
            if len(self.conversations) > self.max_conversations:
                self.conversations = self.conversations[-self.max_conversations:]

            self.save_data()
            self.logger.info(f"Память импортирована из {filepath}")

        except Exception as e:
            self.logger.error(f"Ошибка импорта памяти: {e}")