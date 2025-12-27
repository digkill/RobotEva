"""
Сервис воспроизведения медиа (музыка, видео, YouTube)
"""
import logging
import subprocess
import asyncio
from typing import Optional
import webbrowser
import os


class MediaService:
    """Сервис для воспроизведения медиа"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки медиа
        self.media_player = config.get("services.media.player", "vlc")
        self.youtube_enabled = config.get("services.media.youtube.enabled", True)
        self.music_path = config.get("services.media.music_path", "/home/pi/Music")
        
        self.current_process: Optional[subprocess.Popen] = None
    
    async def initialize(self):
        """Инициализация сервиса"""
        self.logger.info("Сервис медиа инициализирован")
    
    async def play_music(self, query: str):
        """
        Воспроизведение музыки
        
        Args:
            query: Запрос музыки (название трека, исполнитель, жанр)
        """
        try:
            # Поиск музыки локально или в интернете
            music_file = await self._find_music(query)
            
            if music_file:
                await self._play_file(music_file)
            else:
                # Поиск на YouTube
                if self.youtube_enabled:
                    await self.play_youtube(query)
                else:
                    self.logger.warning(f"Музыка не найдена: {query}")
        
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения музыки: {e}")
    
    async def _find_music(self, query: str) -> Optional[str]:
        """Поиск музыки локально"""
        if not os.path.exists(self.music_path):
            return None
        
        query_lower = query.lower()
        
        # Поиск файлов музыки
        for root, dirs, files in os.walk(self.music_path):
            for file in files:
                if file.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a')):
                    if query_lower in file.lower():
                        return os.path.join(root, file)
        
        return None
    
    async def play_video(self, url: str):
        """
        Воспроизведение видео по URL
        
        Args:
            url: URL видео
        """
        try:
            if self.media_player == "vlc":
                await self._play_with_vlc(url)
            elif self.media_player == "omxplayer":
                await self._play_with_omxplayer(url)
            else:
                # Открытие в браузере
                webbrowser.open(url)
        
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения видео: {e}")
    
    async def play_youtube(self, query: str):
        """
        Воспроизведение видео с YouTube
        
        Args:
            query: Поисковый запрос или URL
        """
        try:
            # Проверка, является ли query URL
            if query.startswith(("http://", "https://", "www.youtube.com", "youtu.be")):
                url = query
            else:
                # Поиск видео на YouTube
                url = await self._search_youtube(query)
            
            if url:
                await self.play_video(url)
            else:
                self.logger.warning(f"Видео YouTube не найдено: {query}")
        
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения YouTube: {e}")
    
    async def _search_youtube(self, query: str) -> Optional[str]:
        """Поиск видео на YouTube"""
        try:
            from yt_dlp import YoutubeDL
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                # Поиск
                search_results = ydl.extract_info(
                    f"ytsearch1:{query}",
                    download=False
                )
                
                if search_results and 'entries' in search_results:
                    entry = search_results['entries'][0]
                    return f"https://www.youtube.com/watch?v={entry['id']}"
        
        except ImportError:
            self.logger.warning("yt-dlp не установлен, используйте: pip install yt-dlp")
        except Exception as e:
            self.logger.error(f"Ошибка поиска YouTube: {e}")
        
        return None
    
    async def _play_file(self, file_path: str):
        """Воспроизведение файла"""
        if self.media_player == "vlc":
            await self._play_with_vlc(file_path)
        elif self.media_player == "omxplayer":
            await self._play_with_omxplayer(file_path)
    
    async def _play_with_vlc(self, source: str):
        """Воспроизведение через VLC"""
        try:
            if self.current_process:
                self.current_process.terminate()
            
            self.current_process = subprocess.Popen(
                ["vlc", "--intf", "dummy", "--play-and-exit", source],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        except FileNotFoundError:
            self.logger.error("VLC не установлен")
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения через VLC: {e}")
    
    async def _play_with_omxplayer(self, source: str):
        """Воспроизведение через omxplayer (для Raspberry Pi)"""
        try:
            if self.current_process:
                self.current_process.terminate()
            
            self.current_process = subprocess.Popen(
                ["omxplayer", source],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        except FileNotFoundError:
            self.logger.error("omxplayer не установлен")
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения через omxplayer: {e}")
    
    async def stop(self):
        """Остановка воспроизведения"""
        if self.current_process:
            self.current_process.terminate()
            self.current_process = None
    
    async def cleanup(self):
        """Очистка ресурсов"""
        await self.stop()
        self.logger.info("Сервис медиа остановлен")

