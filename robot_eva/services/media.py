"""
Сервис воспроизведения медиа (музыка, видео, YouTube)
"""
import logging
import subprocess
import asyncio
from typing import Optional, List, Dict
import webbrowser
import os
import json
import time


class MediaService:
    """Сервис для воспроизведения медиа"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки медиа
        self.media_player = config.get("services.media.player", "vlc")
        self.youtube_enabled = config.get("services.media.youtube.enabled", True)
        self.music_path = config.get("services.media.music_path", "/home/pi/Music")
        
        # База данных музыкальных файлов
        data_dir = config.get("data_dir", "/home/pi/Projects/RobotEva/data")
        os.makedirs(data_dir, exist_ok=True)
        self.music_library_path = os.path.join(data_dir, "music_library.json")
        self.music_library: Dict[str, Dict] = {}  # {file_path: {title, artist, album, duration, added_at, modified_at}}
        
        # Настройки сканирования
        self.auto_scan_on_start = config.get("services.media.auto_scan_on_start", True)
        self.scan_interval_seconds = config.get("services.media.scan_interval_seconds", 3600)  # 1 час
        
        self.current_process: Optional[subprocess.Popen] = None
        self._scan_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Инициализация сервиса"""
        # Загружаем библиотеку музыки
        await self._load_music_library()
        
        # Автоматическое сканирование при старте
        if self.auto_scan_on_start:
            self.logger.info("Запуск автоматического сканирования музыкальных файлов...")
            await self.scan_music_files()
        
        # Запускаем периодическое сканирование
        if self.scan_interval_seconds > 0:
            self._scan_task = asyncio.create_task(self._periodic_scan())
        
        self.logger.info("Сервис медиа инициализирован")
    
    async def play_music(self, query: str):
        """
        Воспроизведение музыки
        
        Args:
            query: Запрос музыки (название трека, исполнитель, жанр)
        """
        try:
            q = (query or "").strip()
            if q:
                self.logger.info(f"Play music: query={q!r}")
            # Поиск музыки локально или в интернете
            music_file = await self._find_music(query)
            
            if music_file:
                self.logger.info(f"Play music: local file={music_file}")
                await self._play_file(music_file)
            else:
                # Поиск на YouTube
                if self.youtube_enabled:
                    self.logger.info("Play music: not found locally -> YouTube search")
                    await self.play_youtube(query)
                else:
                    self.logger.warning(f"Музыка не найдена: {query}")
        
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения музыки: {e}")
    
    async def _load_music_library(self):
        """Загрузка библиотеки музыки из файла"""
        try:
            if os.path.exists(self.music_library_path):
                with open(self.music_library_path, 'r', encoding='utf-8') as f:
                    self.music_library = json.load(f)
                self.logger.info(f"Загружено {len(self.music_library)} музыкальных файлов из библиотеки")
            else:
                self.music_library = {}
                self.logger.info("Библиотека музыки пуста, будет создана при сканировании")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки библиотеки музыки: {e}")
            self.music_library = {}
    
    async def _save_music_library(self):
        """Сохранение библиотеки музыки в файл"""
        try:
            with open(self.music_library_path, 'w', encoding='utf-8') as f:
                json.dump(self.music_library, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Библиотека музыки сохранена: {len(self.music_library)} файлов")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения библиотеки музыки: {e}")
    
    async def scan_music_files(self, force_rescan: bool = False) -> int:
        """
        Сканирование музыкальных файлов и добавление в библиотеку
        
        Args:
            force_rescan: Если True, пересканирует все файлы, даже если они уже в библиотеке
        
        Returns:
            Количество добавленных/обновленных файлов
        """
        if not os.path.exists(self.music_path):
            self.logger.warning(f"Путь к музыке не существует: {self.music_path}")
            return 0
        
        self.logger.info(f"Начинаю сканирование музыкальных файлов в {self.music_path}...")
        
        def _scan_files() -> List[str]:
            """Сканирование файловой системы"""
            music_files = []
            extensions = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus")
            for root, _dirs, files in os.walk(self.music_path):
                for file in files:
                    if file.lower().endswith(extensions):
                        file_path = os.path.join(root, file)
                        music_files.append(file_path)
            return music_files
        
        # Сканируем файлы в отдельном потоке
        music_files = await asyncio.to_thread(_scan_files)
        self.logger.info(f"Найдено {len(music_files)} музыкальных файлов")
        
        added_count = 0
        updated_count = 0
        
        for file_path in music_files:
            try:
                # Проверяем, нужно ли обновлять файл
                file_stat = os.stat(file_path)
                file_modified = file_stat.st_mtime
                
                if file_path in self.music_library:
                    if force_rescan or self.music_library[file_path].get("modified_at", 0) < file_modified:
                        # Обновляем существующий файл
                        await self._add_music_file(file_path, file_modified)
                        updated_count += 1
                else:
                    # Добавляем новый файл
                    await self._add_music_file(file_path, file_modified)
                    added_count += 1
            except Exception as e:
                self.logger.warning(f"Ошибка обработки файла {file_path}: {e}")
        
        # Сохраняем библиотеку
        await self._save_music_library()
        
        total = added_count + updated_count
        self.logger.info(f"Сканирование завершено: добавлено {added_count}, обновлено {updated_count}, всего {total}")
        return total
    
    async def _add_music_file(self, file_path: str, modified_at: float):
        """Добавление музыкального файла в библиотеку"""
        try:
            file_name = os.path.basename(file_path)
            file_name_no_ext = os.path.splitext(file_name)[0]
            
            # Пытаемся извлечь метаданные из имени файла
            # Формат: "Artist - Title" или "Title"
            parts = file_name_no_ext.split(" - ", 1)
            if len(parts) == 2:
                artist = parts[0].strip()
                title = parts[1].strip()
            else:
                artist = ""
                title = parts[0].strip()
            
            # Добавляем в библиотеку
            self.music_library[file_path] = {
                "title": title,
                "artist": artist,
                "album": "",
                "duration": 0,  # Можно добавить извлечение через mutagen позже
                "added_at": time.time() if file_path not in self.music_library else self.music_library[file_path].get("added_at", time.time()),
                "modified_at": modified_at,
                "file_name": file_name
            }
        except Exception as e:
            self.logger.warning(f"Ошибка добавления файла {file_path} в библиотеку: {e}")
    
    async def add_music_file(self, file_path: str) -> bool:
        """
        Ручное добавление музыкального файла в библиотеку
        
        Args:
            file_path: Путь к музыкальному файлу
        
        Returns:
            True если файл добавлен, False если ошибка
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Файл не найден: {file_path}")
            return False
        
        try:
            file_stat = os.stat(file_path)
            await self._add_music_file(file_path, file_stat.st_mtime)
            await self._save_music_library()
            self.logger.info(f"Файл добавлен в библиотеку: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка добавления файла {file_path}: {e}")
            return False
    
    async def _periodic_scan(self):
        """Периодическое автоматическое сканирование"""
        while True:
            try:
                await asyncio.sleep(self.scan_interval_seconds)
                self.logger.info("Запуск периодического сканирования музыкальных файлов...")
                await self.scan_music_files(force_rescan=False)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Ошибка периодического сканирования: {e}")
    
    async def _find_music(self, query: str) -> Optional[str]:
        """Поиск музыки локально (использует библиотеку)"""
        if not self.music_library:
            # Если библиотека пуста, делаем быстрый поиск по файловой системе
            return await self._find_music_fallback(query)
        
        q = (query or "").strip().lower()
        if not q:
            return None
        
        # Поиск в библиотеке
        for file_path, metadata in self.music_library.items():
            if not os.path.exists(file_path):
                # Файл удален, пропускаем
                continue
            
            # Поиск по названию, исполнителю, имени файла
            title = metadata.get("title", "").lower()
            artist = metadata.get("artist", "").lower()
            file_name = metadata.get("file_name", "").lower()
            
            if q in title or q in artist or q in file_name:
                return file_path
        
        # Если не найдено в библиотеке, делаем fallback поиск
        return await self._find_music_fallback(query)
    
    async def _find_music_fallback(self, query: str) -> Optional[str]:
        """Fallback поиск по файловой системе (если библиотека пуста)"""
        if not os.path.exists(self.music_path):
            return None

        q = (query or "").strip().lower()
        if not q:
            return None

        def _scan() -> Optional[str]:
            # Поиск файлов музыки
            for root, _dirs, files in os.walk(self.music_path):
                for file in files:
                    fl = file.lower()
                    if fl.endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a")) and (q in fl):
                        return os.path.join(root, file)
            return None

        # os.walk может быть медленным — не блокируем event loop.
        return await asyncio.to_thread(_scan)
    
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

            q = (query or "").strip()
            if not q:
                return None

            def _run() -> Optional[str]:
                with YoutubeDL(ydl_opts) as ydl:
                    search_results = ydl.extract_info(
                        f"ytsearch1:{q}",
                        download=False
                    )
                    if search_results and "entries" in search_results and search_results["entries"]:
                        entry = search_results["entries"][0]
                        if entry and entry.get("id"):
                            return f"https://www.youtube.com/watch?v={entry['id']}"
                return None

            # yt-dlp может долго висеть на сети/днс — запускаем в thread и ограничиваем таймаутом.
            try:
                timeout_s = float(self.config.get("services.media.youtube.search_timeout_seconds", 12))
            except Exception:
                timeout_s = 12.0
            timeout_s = max(3.0, min(60.0, timeout_s))

            return await asyncio.wait_for(asyncio.to_thread(_run), timeout=timeout_s)
        
        except ImportError:
            self.logger.warning("yt-dlp не установлен, используйте: pip install yt-dlp")
        except asyncio.TimeoutError:
            self.logger.warning("Таймаут поиска YouTube (yt-dlp)")
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
        # Останавливаем периодическое сканирование
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        
        # Сохраняем библиотеку перед выходом
        await self._save_music_library()
        
        await self.stop()
        self.logger.info("Сервис медиа остановлен")
    
    async def get_music_library_stats(self) -> Dict:
        """Получить статистику библиотеки музыки"""
        total_files = len(self.music_library)
        existing_files = sum(1 for path in self.music_library.keys() if os.path.exists(path))
        return {
            "total_files": total_files,
            "existing_files": existing_files,
            "missing_files": total_files - existing_files,
            "music_path": self.music_path
        }

