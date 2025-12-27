"""
Сервис поиска информации в интернете
"""
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote


class InternetService:
    """Сервис для поиска информации в интернете"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки поиска
        self.search_engine = config.get("services.internet.search_engine", "duckduckgo")
        self.max_results = config.get("services.internet.max_results", 5)
        
        # API ключи для различных поисковых систем
        self.google_api_key = config.get("services.internet.google.api_key", "")
        self.google_cx = config.get("services.internet.google.cx", "")
    
    async def initialize(self):
        """Инициализация сервиса"""
        self.logger.info("Сервис интернет-поиска инициализирован")
    
    async def search(self, query: str) -> List[Dict]:
        """
        Поиск информации в интернете
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список результатов поиска
        """
        try:
            if self.search_engine == "google" and self.google_api_key:
                return await self._search_google(query)
            else:
                return await self._search_duckduckgo(query)
        
        except Exception as e:
            self.logger.error(f"Ошибка поиска: {e}")
            return []
    
    async def _search_google(self, query: str) -> List[Dict]:
        """Поиск через Google Custom Search API"""
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cx,
                "q": query,
                "num": self.max_results
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("items", [])[:self.max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "link": item.get("link", "")
                    })
                
                return results
        
        except Exception as e:
            self.logger.error(f"Ошибка поиска Google: {e}")
        
        return []
    
    async def _search_duckduckgo(self, query: str) -> List[Dict]:
        """Поиск через DuckDuckGo (без API ключа)"""
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = []
                for result in ddgs.text(query, max_results=self.max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("body", ""),
                        "link": result.get("href", "")
                    })
                
                return results
        
        except ImportError:
            self.logger.warning("DuckDuckGo search не установлен, используйте: pip install duckduckgo-search")
        except Exception as e:
            self.logger.error(f"Ошибка поиска DuckDuckGo: {e}")
        
        return []
    
    async def get_weather(self, location: str = "Москва") -> Optional[Dict]:
        """Получение информации о погоде"""
        try:
            # Использование OpenWeatherMap API или другого сервиса
            api_key = self.config.get("services.internet.weather.api_key", "")
            if not api_key:
                # Альтернатива: поиск погоды через обычный поиск
                results = await self.search(f"погода {location}")
                if results:
                    return {
                        "location": location,
                        "info": results[0].get("snippet", "")
                    }
                return None
            
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": api_key,
                "units": "metric",
                "lang": "ru"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "location": location,
                    "temperature": data["main"]["temp"],
                    "description": data["weather"][0]["description"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data.get("wind", {}).get("speed", 0)
                }
        
        except Exception as e:
            self.logger.error(f"Ошибка получения погоды: {e}")
        
        return None

