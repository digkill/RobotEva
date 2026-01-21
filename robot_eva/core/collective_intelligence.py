"""
Коллективный интеллект - обмен знаниями между роботами
"""
import logging
import asyncio
import json
import time
import os
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
import aiohttp
import hashlib


@dataclass
class KnowledgePacket:
    """Пакет знаний для обмена"""
    id: str
    source_robot: str
    timestamp: float
    knowledge_type: str  # "pattern", "behavior", "emotion", "reflection", "skill"
    content: Dict[str, Any]
    confidence: float  # 0.0 - 1.0
    tags: List[str]
    version: int = 1

    def __post_init__(self):
        if not self.id:
            # Генерируем ID на основе контента
            content_hash = hashlib.md5(json.dumps(self.content, sort_keys=True).encode()).hexdigest()
            self.id = f"{self.knowledge_type}_{content_hash[:8]}"


@dataclass
class RobotPeer:
    """Информация о пире (другом роботе)"""
    id: str
    name: str
    address: str  # IP:port
    last_seen: float
    capabilities: List[str]
    trust_level: float  # 0.0 - 1.0
    shared_knowledge_count: int = 0


class CollectiveIntelligence:
    """
    Система коллективного интеллекта

    Обеспечивает:
    - Обмен знаниями между экземплярами RobotEva
    - Синхронизацию обученных паттернов
    - Распределенное обучение
    - Сетевой API для коммуникации
    """

    def __init__(self, config, robot_id: str = None, consciousness_ref=None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.consciousness = consciousness_ref

        # Идентификация робота
        self.robot_id = robot_id or f"robot_{int(time.time())}"
        self.robot_name = config.get("robot.name", "Eva")

        # Сеть
        self.host = config.get("network.collective.host", "0.0.0.0")
        self.port = int(config.get("network.collective.port", 8888))
        self.peers: Dict[str, RobotPeer] = {}
        self.server = None
        self.session: Optional[aiohttp.ClientSession] = None

        # Знания
        self.knowledge_base: Dict[str, KnowledgePacket] = {}
        self.shared_knowledge: Set[str] = set()
        self.pending_exchanges: List[Dict] = []

        # Статистика
        self.stats = {
            "total_packets_shared": 0,
            "total_packets_received": 0,
            "active_peers": 0,
            "knowledge_synced": 0
        }

        # Настройки
        self.enabled = config.get("collective_intelligence.enabled", False)
        self.auto_discovery = config.get("collective_intelligence.auto_discovery", True)
        self.sync_interval = int(config.get("collective_intelligence.sync_interval", 300))  # 5 минут
        self.trust_threshold = float(config.get("collective_intelligence.trust_threshold", 0.7))

        # Пути к данным
        self.data_path = "/home/pi/Projects/RobotEva/data/collective"
        self.knowledge_file = os.path.join(self.data_path, "knowledge_base.json")
        self.peers_file = os.path.join(self.data_path, "peers.json")

        # Создаем директорию
        os.makedirs(self.data_path, exist_ok=True)

        # Загружаем данные
        self._load_data()

    async def initialize(self):
        """Инициализация коллективного интеллекта"""
        if not self.enabled:
            self.logger.info("Коллективный интеллект отключен")
            return

        self.logger.info(f"Инициализация коллективного интеллекта (ID: {self.robot_id})")

        # Создаем HTTP сессию
        self.session = aiohttp.ClientSession()

        # Запускаем сервер
        await self._start_server()

        # Загружаем пиров
        await self._load_peers()

        # Запускаем фоновые задачи
        asyncio.create_task(self._sync_loop())
        asyncio.create_task(self._discovery_loop())

        self.logger.info(f"Коллективный интеллект активен на {self.host}:{self.port}")

    async def _start_server(self):
        """Запустить HTTP сервер для приема знаний"""
        from aiohttp import web

        app = web.Application()

        # Роуты
        app.router.add_get('/health', self._handle_health)
        app.router.add_get('/peers', self._handle_get_peers)
        app.router.add_post('/knowledge', self._handle_receive_knowledge)
        app.router.add_get('/knowledge', self._handle_get_knowledge)
        app.router.add_post('/sync', self._handle_sync_request)

        # Запускаем сервер
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self.logger.info(f"Сервер коллективного интеллекта запущен на порту {self.port}")

    async def _handle_health(self, request):
        """Обработчик проверки здоровья"""
        return web.json_response({
            "robot_id": self.robot_id,
            "robot_name": self.robot_name,
            "status": "healthy",
            "knowledge_count": len(self.knowledge_base),
            "peers_count": len(self.peers),
            "timestamp": time.time()
        })

    async def _handle_get_peers(self, request):
        """Получить список известных пиров"""
        peers_info = []
        for peer_id, peer in self.peers.items():
            peers_info.append({
                "id": peer.id,
                "name": peer.name,
                "address": peer.address,
                "last_seen": peer.last_seen,
                "capabilities": peer.capabilities,
                "trust_level": peer.trust_level
            })

        return web.json_response({"peers": peers_info})

    async def _handle_receive_knowledge(self, request):
        """Принять пакет знаний"""
        try:
            data = await request.json()
            packet_data = data.get("packet")

            if not packet_data:
                return web.json_response({"error": "No packet provided"}, status=400)

            # Создаем пакет знаний
            packet = KnowledgePacket(**packet_data)

            # Проверяем, не получали ли уже этот пакет
            if packet.id in self.knowledge_base:
                return web.json_response({"status": "already_have"})

            # Добавляем в базу знаний
            await self._add_knowledge_packet(packet, source="network")

            self.stats["total_packets_received"] += 1

            return web.json_response({"status": "accepted", "packet_id": packet.id})

        except Exception as e:
            self.logger.error(f"Ошибка приема знаний: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_get_knowledge(self, request):
        """Отправить пакеты знаний"""
        # Отправляем недавно добавленные пакеты
        recent_packets = []
        cutoff_time = time.time() - 3600  # Последний час

        for packet in self.knowledge_base.values():
            if packet.timestamp > cutoff_time and packet.id not in self.shared_knowledge:
                recent_packets.append(asdict(packet))
                self.shared_knowledge.add(packet.id)

        return web.json_response({"packets": recent_packets})

    async def _handle_sync_request(self, request):
        """Обработчик запроса синхронизации"""
        try:
            data = await request.json()
            peer_id = data.get("peer_id")

            if peer_id:
                await self._sync_with_peer(peer_id)

            return web.json_response({"status": "sync_initiated"})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    def _load_data(self):
        """Загрузка данных из файлов"""
        try:
            # Загружаем базу знаний
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pid, packet_data in data.get("knowledge", {}).items():
                        packet = KnowledgePacket(**packet_data)
                        self.knowledge_base[pid] = packet

            # Загружаем пиров
            if os.path.exists(self.peers_file):
                with open(self.peers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pid, peer_data in data.get("peers", {}).items():
                        peer = RobotPeer(**peer_data)
                        self.peers[pid] = peer

        except Exception as e:
            self.logger.warning(f"Ошибка загрузки данных коллективного интеллекта: {e}")

    async def _load_peers(self):
        """Загрузка списка известных пиров"""
        # В будущем можно добавить загрузку из конфига или discovery
        known_peers = self.config.get("collective_intelligence.known_peers", [])

        for peer_config in known_peers:
            peer = RobotPeer(
                id=peer_config.get("id"),
                name=peer_config.get("name"),
                address=peer_config.get("address"),
                last_seen=0.0,
                capabilities=peer_config.get("capabilities", []),
                trust_level=peer_config.get("trust_level", 0.8)
            )
            self.peers[peer.id] = peer

    def save_data(self):
        """Сохранение данных"""
        try:
            # Сохраняем базу знаний
            knowledge_data = {
                "knowledge": {pid: asdict(packet) for pid, packet in self.knowledge_base.items()},
                "saved_at": time.time()
            }
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(knowledge_data, f, indent=2, ensure_ascii=False)

            # Сохраняем пиров
            peers_data = {
                "peers": {pid: asdict(peer) for pid, peer in self.peers.items()},
                "saved_at": time.time()
            }
            with open(self.peers_file, 'w', encoding='utf-8') as f:
                json.dump(peers_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Ошибка сохранения данных коллективного интеллекта: {e}")

    async def _sync_loop(self):
        """Цикл синхронизации с пирами"""
        while True:
            try:
                if self.peers:
                    # Синхронизируемся со случайным пиром
                    peer_ids = list(self.peers.keys())
                    peer_id = peer_ids[int(time.time()) % len(peer_ids)]

                    await self._sync_with_peer(peer_id)

                await asyncio.sleep(self.sync_interval)

            except Exception as e:
                self.logger.warning(f"Ошибка в цикле синхронизации: {e}")
                await asyncio.sleep(60)

    async def _discovery_loop(self):
        """Цикл обнаружения новых пиров"""
        if not self.auto_discovery:
            return

        while True:
            try:
                # Сканируем локальную сеть на известные порты
                await self._network_discovery()

                # Проверяем здоровье существующих пиров
                await self._check_peer_health()

                await asyncio.sleep(300)  # Каждые 5 минут

            except Exception as e:
                self.logger.warning(f"Ошибка в цикле обнаружения: {e}")
                await asyncio.sleep(60)

    async def _network_discovery(self):
        """Сканирование сети для обнаружения пиров"""
        # Упрощенная реализация - в будущем можно добавить более сложную логику
        # Например, сканирование UDP broadcast или использование mDNS

        # Для демонстрации добавляем тестового пира
        if "test_peer" not in self.peers:
            test_peer = RobotPeer(
                id="test_peer",
                name="TestRobot",
                address="127.0.0.1:8889",  # Для тестирования
                last_seen=time.time(),
                capabilities=["social_learning", "creativity"],
                trust_level=0.9
            )
            self.peers[test_peer.id] = test_peer
            self.logger.info(f"Обнаружен новый пир: {test_peer.name}")

    async def _check_peer_health(self):
        """Проверка здоровья пиров"""
        unhealthy_peers = []

        for peer_id, peer in self.peers.items():
            try:
                # Проверяем здоровье пира
                async with self.session.get(f"http://{peer.address}/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        peer.last_seen = time.time()
                        # Обновляем информацию о пире
                        if "capabilities" in data:
                            peer.capabilities = data["capabilities"]
                    else:
                        unhealthy_peers.append(peer_id)

            except Exception:
                unhealthy_peers.append(peer_id)

        # Удаляем неработающие пиры
        for peer_id in unhealthy_peers:
            if peer_id in self.peers:
                del self.peers[peer_id]
                self.logger.warning(f"Пир {peer_id} недоступен, удален из списка")

    async def _sync_with_peer(self, peer_id: str):
        """Синхронизация с конкретным пиром"""
        if peer_id not in self.peers:
            return

        peer = self.peers[peer_id]

        try:
            # Получаем новые знания от пира
            async with self.session.get(f"http://{peer.address}/knowledge", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    packets = data.get("packets", [])

                    for packet_data in packets:
                        packet = KnowledgePacket(**packet_data)

                        # Проверяем доверие и добавляем
                        if packet.confidence >= self.trust_threshold:
                            await self._add_knowledge_packet(packet, source="sync")
                            self.stats["total_packets_received"] += 1

            # Отправляем наши новые знания
            if self.knowledge_base:
                recent_packets = []
                cutoff_time = time.time() - 3600  # Последний час

                for packet in self.knowledge_base.values():
                    if packet.timestamp > cutoff_time and packet.id not in self.shared_knowledge:
                        recent_packets.append(asdict(packet))
                        self.shared_knowledge.add(packet.id)

                if recent_packets:
                    async with self.session.post(
                        f"http://{peer.address}/knowledge",
                        json={"packets": recent_packets},
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            self.stats["total_packets_shared"] += len(recent_packets)
                            peer.shared_knowledge_count += len(recent_packets)

            self.logger.debug(f"Синхронизация с {peer.name} завершена")

        except Exception as e:
            self.logger.warning(f"Ошибка синхронизации с {peer.name}: {e}")

    async def share_knowledge(self, knowledge_type: str, content: Dict[str, Any],
                            confidence: float = 0.8, tags: List[str] = None) -> str:
        """
        Поделиться знанием с коллективом

        Args:
            knowledge_type: Тип знания
            content: Содержимое
            confidence: Уровень уверенности
            tags: Теги для поиска

        Returns:
            ID созданного пакета
        """
        if tags is None:
            tags = []

        packet = KnowledgePacket(
            id="",  # Будет сгенерирован автоматически
            source_robot=self.robot_id,
            timestamp=time.time(),
            knowledge_type=knowledge_type,
            content=content,
            confidence=confidence,
            tags=tags
        )

        # Добавляем в локальную базу
        packet_id = await self._add_knowledge_packet(packet, source="local")

        # Отправляем пирам
        await self._broadcast_knowledge(packet)

        return packet_id

    async def _add_knowledge_packet(self, packet: KnowledgePacket, source: str = "local"):
        """Добавить пакет знаний в базу"""
        # Проверяем, есть ли уже такая версия
        if packet.id in self.knowledge_base:
            existing = self.knowledge_base[packet.id]
            if packet.version <= existing.version:
                return packet.id  # Уже есть более новая версия

        # Добавляем/обновляем
        self.knowledge_base[packet.id] = packet

        # Интегрируем знание в сознание робота
        await self._integrate_knowledge(packet)

        # Сохраняем
        self.save_data()

        self.logger.info(f"Добавлено знание {packet.knowledge_type} от {source}: {packet.id}")
        return packet.id

    async def _integrate_knowledge(self, packet: KnowledgePacket):
        """Интегрировать полученное знание в сознание робота"""
        if not self.consciousness:
            return

        try:
            knowledge_type = packet.knowledge_type
            content = packet.content

            if knowledge_type == "pattern":
                # Добавляем паттерн в learning engine
                if hasattr(self.consciousness, 'learning_engine'):
                    await self.consciousness.learning_engine.record_experience(
                        situation=content.get("situation", "unknown"),
                        action_taken=content.get("action", "unknown"),
                        outcome=content.get("outcome", "unknown"),
                        success=content.get("success", True)
                    )

            elif knowledge_type == "behavior":
                # Добавляем поведение
                if hasattr(self.consciousness, 'learning_engine'):
                    self.consciousness.learning_engine.behaviors[packet.id] = content.get("code", "")

            elif knowledge_type == "emotion":
                # Добавляем эмоцию
                if hasattr(self.consciousness, 'emotion_engine'):
                    emotion_name = content.get("name", "unknown")
                    # Создаем эмоцию если её нет
                    if hasattr(self.consciousness.emotion_engine, 'create_emotion'):
                        await self.consciousness.emotion_engine.create_emotion(
                            name=emotion_name,
                            description=content.get("description", ""),
                            valence=content.get("valence", 0.0),
                            arousal=content.get("arousal", 0.5),
                            display_expression=content.get("display", {}),
                            behavior_modifiers=content.get("modifiers", {})
                        )

            elif knowledge_type == "reflection":
                # Добавляем рефлексию
                if hasattr(self.consciousness, 'reflection_engine'):
                    reflection = await self.consciousness.reflection_engine.reflect(
                        topic=content.get("topic", "Shared reflection"),
                        context=content.get("context", {}),
                        llm_service=getattr(self.consciousness, 'llm_service', None)
                    )
                    self.logger.info(f"Интегрирована коллективная рефлексия: {reflection.topic}")

        except Exception as e:
            self.logger.warning(f"Ошибка интеграции знания {packet.id}: {e}")

    async def _broadcast_knowledge(self, packet: KnowledgePacket):
        """Отправить знание всем известным пирам"""
        if not self.peers:
            return

        packet_data = {"packet": asdict(packet)}

        for peer_id, peer in self.peers.items():
            try:
                async with self.session.post(
                    f"http://{peer.address}/knowledge",
                    json=packet_data,
                    timeout=5
                ) as response:
                    if response.status == 200:
                        self.stats["total_packets_shared"] += 1
                        peer.shared_knowledge_count += 1

            except Exception as e:
                self.logger.debug(f"Не удалось отправить знание пиру {peer.name}: {e}")

    async def query_knowledge(self, query: str, knowledge_type: str = None,
                            tags: List[str] = None) -> List[KnowledgePacket]:
        """
        Поиск знаний в коллективе

        Args:
            query: Поисковый запрос
            knowledge_type: Тип знания для фильтрации
            tags: Теги для фильтрации

        Returns:
            Найденные пакеты знаний
        """
        results = []

        for packet in self.knowledge_base.values():
            # Фильтры
            if knowledge_type and packet.knowledge_type != knowledge_type:
                continue

            if tags and not any(tag in packet.tags for tag in tags):
                continue

            # Поиск по контенту (упрощенная версия)
            content_str = json.dumps(packet.content, ensure_ascii=False).lower()
            if query.lower() in content_str:
                results.append(packet)

        # Сортируем по confidence
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results[:10]  # Топ-10 результатов

    async def request_knowledge(self, query: str, knowledge_type: str = None) -> List[KnowledgePacket]:
        """
        Запросить знание у пиров

        Args:
            query: Запрос
            knowledge_type: Тип знания

        Returns:
            Найденные знания
        """
        # Сначала ищем локально
        local_results = await self.query_knowledge(query, knowledge_type)

        # Если нашли достаточно, возвращаем
        if len(local_results) >= 3:
            return local_results

        # Запрашиваем у пиров
        all_results = list(local_results)

        for peer_id, peer in self.peers.items():
            try:
                # Отправляем запрос на поиск
                request_data = {
                    "query": query,
                    "type": knowledge_type,
                    "requestor": self.robot_id
                }

                async with self.session.post(
                    f"http://{peer.address}/search",
                    json=request_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        peer_results = data.get("results", [])

                        for result_data in peer_results:
                            packet = KnowledgePacket(**result_data)
                            all_results.append(packet)

            except Exception as e:
                self.logger.debug(f"Ошибка запроса к пиру {peer.name}: {e}")

        # Убираем дубликаты и сортируем
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result.id not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result.id)

        unique_results.sort(key=lambda x: x.confidence, reverse=True)

        return unique_results[:10]

    def get_collective_stats(self) -> Dict[str, Any]:
        """Получить статистику коллективного интеллекта"""
        return {
            "robot_id": self.robot_id,
            "enabled": self.enabled,
            "knowledge_packets": len(self.knowledge_base),
            "known_peers": len(self.peers),
            "active_peers": len([p for p in self.peers.values()
                               if time.time() - p.last_seen < 300]),  # Активные за 5 минут
            "total_shared": self.stats["total_packets_shared"],
            "total_received": self.stats["total_packets_received"],
            "sync_interval": self.sync_interval
        }

    async def shutdown(self):
        """Завершение работы"""
        if self.session:
            await self.session.close()

        self.save_data()
        self.logger.info("Коллективный интеллект завершен")