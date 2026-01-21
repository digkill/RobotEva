"""
Сервис поиска информации в интернете
"""
import logging
import base64
from typing import List, Dict, Optional
from urllib.parse import quote

from ..utils.http_client import create_requests_session


class InternetService:
    """Сервис для поиска информации в интернете"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.http = create_requests_session(config)
        
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
            
            timeout = float(self.config.get("network.http.timeout_seconds", 10))
            import asyncio
            response = await asyncio.to_thread(self.http.get, url, params=params, timeout=timeout)
            
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
            
            import asyncio

            def _run():
                with DDGS() as ddgs:
                    results = []
                    for result in ddgs.text(query, max_results=self.max_results):
                        results.append({
                            "title": result.get("title", ""),
                            "snippet": result.get("body", ""),
                            "link": result.get("href", "")
                        })
                    return results

            return await asyncio.to_thread(_run)
        
        except ImportError:
            self.logger.warning("DuckDuckGo search не установлен, используйте: pip install duckduckgo-search")
        except Exception as e:
            # Частая причина: 403/блок по IP. Делаем мягкий fallback на Instant Answer API.
            self.logger.warning(f"Ошибка поиска DuckDuckGo (возможно 403): {e}")
            try:
                timeout = float(self.config.get("network.http.timeout_seconds", 10))
                url = "https://api.duckduckgo.com/"
                params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
                import asyncio
                r = await asyncio.to_thread(self.http.get, url, params=params, timeout=timeout)
                if r.status_code != 200:
                    return []
                data = r.json() or {}
                results = []
                abstract = (data.get("AbstractText") or "").strip()
                abstract_url = (data.get("AbstractURL") or "").strip()
                heading = (data.get("Heading") or "").strip() or query
                if abstract:
                    results.append({"title": heading, "snippet": abstract, "link": abstract_url})
                for t in (data.get("RelatedTopics") or [])[: self.max_results]:
                    if isinstance(t, dict) and t.get("Text") and t.get("FirstURL"):
                        results.append({"title": heading, "snippet": t["Text"], "link": t["FirstURL"]})
                    if len(results) >= self.max_results:
                        break
                return results[: self.max_results]
            except Exception:
                return []
        
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
            
            timeout = float(self.config.get("network.http.timeout_seconds", 10))
            import asyncio
            response = await asyncio.to_thread(self.http.get, url, params=params, timeout=timeout)
            
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

    async def reverse_image_search(self, image_data: bytes, search_engine: str = "google") -> List[Dict]:
        """
        Поиск по изображению (reverse image search)

        Args:
            image_data: Байты изображения
            search_engine: Поисковая система ("google", "yandex", "bing")

        Returns:
            Список результатов поиска
        """
        try:
            if search_engine == "google":
                return await self._reverse_search_google(image_data)
            elif search_engine == "yandex":
                return await self._reverse_search_yandex(image_data)
            elif search_engine == "bing":
                return await self._reverse_search_bing(image_data)
            else:
                # Fallback to Google
                return await self._reverse_search_google(image_data)

        except Exception as e:
            self.logger.error(f"Ошибка поиска по изображению: {e}")
            return []

    async def _reverse_search_google(self, image_data: bytes) -> List[Dict]:
        """Google Reverse Image Search через API"""
        try:
            # Конвертация в base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Google Custom Search API не поддерживает reverse image search напрямую
            # Используем альтернативный подход через поиск по описанию лица

            # Сначала получаем описание лица через vision сервис
            if hasattr(self, '_get_vision_service'):
                vision = self._get_vision_service()
                if vision:
                    import cv2
                    import numpy as np
                    import io

                    # Конвертация bytes в numpy array
                    nparr = np.frombuffer(image_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Получаем описание лица
                    description = await vision.describe_scene(
                        img,
                        prompt="Опиши внешность этого человека: возраст, пол, цвет волос, цвет глаз, особенности лица, одежду. Будь максимально конкретным.",
                        language="ru",
                        max_tokens=200
                    )

                    if description:
                        # Ищем по текстовому описанию
                        search_query = f"человек {description}"
                        return await self.search(search_query)

            # Fallback: поиск через images.google.com
            # Это не идеально, но лучше чем ничего
            url = "https://www.google.com/searchbyimage/upload"
            files = {'encoded_image': ('image.jpg', image_data, 'image/jpeg')}

            timeout = float(self.config.get("network.http.timeout_seconds", 30))
            import asyncio
            response = await asyncio.to_thread(
                self.http.post,
                url,
                files=files,
                timeout=timeout
            )

            if response.status_code == 200:
                # Парсим результаты (упрощенная версия)
                # В реальности нужно парсить HTML или использовать Selenium
                return [{
                    "title": "Результаты поиска по изображению",
                    "snippet": "Найдены похожие изображения. Для детального поиска используйте браузер.",
                    "link": response.url
                }]

        except Exception as e:
            self.logger.error(f"Ошибка Google reverse search: {e}")

        return []

    async def _reverse_search_yandex(self, image_data: bytes) -> List[Dict]:
        """Yandex Reverse Image Search"""
        try:
            # Yandex Images API
            url = "https://yandex.ru/images/search"

            # Конвертация в base64 для URL
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_base64}"

            params = {
                "rpt": "imageview",
                "url": image_url
            }

            timeout = float(self.config.get("network.http.timeout_seconds", 30))
            import asyncio
            response = await asyncio.to_thread(
                self.http.get,
                url,
                params=params,
                timeout=timeout
            )

            if response.status_code == 200:
                return [{
                    "title": "Yandex поиск по изображению",
                    "snippet": "Найдены результаты поиска по изображению через Yandex",
                    "link": response.url
                }]

        except Exception as e:
            self.logger.error(f"Ошибка Yandex reverse search: {e}")

        return []

    async def _reverse_search_bing(self, image_data: bytes) -> List[Dict]:
        """Bing Visual Search"""
        try:
            url = "https://www.bing.com/images/search"

            # Конвертация в base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_base64}"

            params = {
                "view": "detailv2",
                "iss": "sbiupload",
                "sbisrc": "UrlPaste",
                "q": "imgurl:" + image_url
            }

            timeout = float(self.config.get("network.http.timeout_seconds", 30))
            import asyncio
            response = await asyncio.to_thread(
                self.http.get,
                url,
                params=params,
                timeout=timeout
            )

            if response.status_code == 200:
                return [{
                    "title": "Bing Visual Search",
                    "snippet": "Найдены результаты визуального поиска через Bing",
                    "link": response.url
                }]

        except Exception as e:
            self.logger.error(f"Ошибка Bing reverse search: {e}")

        return []

    def _get_vision_service(self):
        """Получить vision сервис для описания изображений"""
        # Это будет установлено из основного робота
        return getattr(self, '_vision_service', None)

    def set_vision_service(self, vision_service):
        """Установить ссылку на vision сервис"""
        self._vision_service = vision_service
