"""
Интеграция с LLM (Grok API) для генерации ответов
"""
import logging
import requests
import json
from typing import Optional, Dict, Any, List


class LLMService:
    """Сервис для работы с LLM через Grok API"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.api_key = config.get("ai.grok.api_key", "")
        self.api_url = config.get("ai.grok.api_url", "https://api.x.ai/v1/chat/completions")
        self.model = config.get("ai.grok.model", "grok-beta")
        self.temperature = config.get("ai.grok.temperature", 0.7)
        self.max_tokens = config.get("ai.grok.max_tokens", 1000)
        
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = config.get("ai.grok.max_history", 10)
    
    async def initialize(self):
        """Инициализация сервиса"""
        if not self.api_key:
            self.logger.warning("Grok API ключ не установлен")
        else:
            self.logger.info("LLM сервис инициализирован")
    
    async def generate_response(self, user_input: str, context: Optional[Dict] = None) -> str:
        """
        Генерация ответа на основе пользовательского ввода
        
        Args:
            user_input: Ввод пользователя
            context: Дополнительный контекст (результаты поиска, действия и т.д.)
            
        Returns:
            Сгенерированный ответ
        """
        if not self.api_key:
            return "Извините, сервис генерации ответов недоступен"
        
        try:
            # Формирование системного промпта
            system_prompt = self._build_system_prompt(context)
            
            # Добавление в историю
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Ограничение истории
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            # Формирование сообщений
            messages = [
                {"role": "system", "content": system_prompt}
            ] + self.conversation_history[-self.max_history:]
            
            # Вызов API
            response = await self._call_api(messages)
            
            if response:
                answer = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Добавление ответа в историю
                self.conversation_history.append({
                    "role": "assistant",
                    "content": answer
                })
                
                return answer
            
            return "Извините, не удалось сгенерировать ответ"
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации ответа: {e}")
            return "Произошла ошибка при генерации ответа"
    
    async def process_command(self, command: str) -> Dict[str, Any]:
        """
        Обработка команды и извлечение действий
        
        Args:
            command: Команда пользователя
            
        Returns:
            Словарь с ответом и действиями
        """
        if not self.api_key:
            return {"response": "", "actions": []}
        
        try:
            # Промпт для извлечения действий
            action_prompt = f"""Проанализируй команду пользователя и определи, какие действия нужно выполнить.
Команда: {command}

Верни JSON с полями:
- response: текстовый ответ
- actions: массив действий, каждое действие имеет:
  - type: тип действия (smart_home, search, play_music, play_video, servo_move)
  - command/query/url/angle: параметры действия
  - servo: номер сервопривода (для servo_move)

Примеры действий:
- smart_home: {{"type": "smart_home", "command": "включить свет в гостиной"}}
- search: {{"type": "search", "query": "погода в Москве"}}
- play_music: {{"type": "play_music", "query": "классическая музыка"}}
- servo_move: {{"type": "servo_move", "servo": 0, "angle": 45}}

Верни только JSON, без дополнительного текста."""
            
            messages = [
                {"role": "system", "content": "Ты помощник для робота. Анализируй команды и возвращай JSON с действиями."},
                {"role": "user", "content": action_prompt}
            ]
            
            response = await self._call_api(messages)
            
            if response:
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Парсинг JSON из ответа
                try:
                    # Извлечение JSON из текста
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        return result
                except json.JSONDecodeError:
                    pass
            
            return {"response": "", "actions": []}
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки команды: {e}")
            return {"response": "", "actions": []}
    
    async def detect_emotion(self, text: str) -> str:
        """
        Определение эмоции из текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Название эмоции
        """
        # Простой анализ эмоций по ключевым словам
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["рад", "хорошо", "отлично", "прекрасно", "ура"]):
            return "happy"
        elif any(word in text_lower for word in ["грустно", "печально", "жаль", "извини"]):
            return "sad"
        elif any(word in text_lower for word in ["удивлен", "невероятно", "вау"]):
            return "surprised"
        elif any(word in text_lower for word in ["думаю", "подумаю", "анализирую"]):
            return "thinking"
        else:
            return "neutral"
    
    async def generate_greeting(self) -> str:
        """Генерация приветствия"""
        greetings = [
            "Привет! Я Eva, твой робот-ассистент. Чем могу помочь?",
            "Здравствуй! Я Eva. Готова помочь с любыми вопросами!",
            "Привет! Рада тебя видеть! Я Eva, твой помощник.",
        ]
        import random
        return random.choice(greetings)
    
    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Построение системного промпта"""
        prompt = """Ты Eva - дружелюбный робот-ассистент. 
Ты помогаешь пользователю с различными задачами: управление умным домом, поиск информации, воспроизведение медиа.
Будь вежливой, дружелюбной и полезной. Отвечай кратко и по делу."""
        
        if context:
            if context.get("search_results"):
                prompt += f"\nРезультаты поиска: {context['search_results']}"
        
        return prompt
    
    async def _call_api(self, messages: List[Dict[str, str]]) -> Optional[Dict]:
        """Вызов Grok API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка вызова API: {e}")
            return None

