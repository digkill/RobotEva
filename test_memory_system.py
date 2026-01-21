#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы памяти контекста
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.context_memory import ContextMemorySystem
from robot_eva.core.config import Config


async def test_memory_system():
    """Тестирование системы памяти"""
    print("🧠 Тестирование системы памяти контекста...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем систему памяти
    memory_system = ContextMemorySystem(config)

    print("✅ Система памяти инициализирована")

    # Тестируем запись взаимодействий
    print("\n📝 Записываем тестовые взаимодействия...")

    test_interactions = [
        {
            "user_input": "Какой сегодня день?",
            "robot_response": "Сегодня вторник, 14 января 2025 года.",
            "context": {"topic": "date", "action_results": {"success": True}},
            "success_rating": 0.9
        },
        {
            "user_input": "Расскажи шутку",
            "robot_response": "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25!",
            "context": {"topic": "humor", "action_results": {"success": True}},
            "success_rating": 0.8
        },
        {
            "user_input": "Как погода?",
            "robot_response": "Я не имею доступа к данным о погоде в реальном времени.",
            "context": {"topic": "weather", "action_results": {"success": False}},
            "success_rating": 0.4
        }
    ]

    for interaction in test_interactions:
        await memory_system.record_interaction(
            user_input=interaction["user_input"],
            robot_response=interaction["robot_response"],
            input_type="voice",
            context_data=interaction["context"],
            success_rating=interaction["success_rating"]
        )
        print(f"   ✅ Записано: {interaction['user_input'][:30]}...")

    # Тестируем поиск релевантного контекста
    print("\n🔍 Тестируем поиск релевантного контекста...")

    queries = ["день", "шутка", "погода"]
    for query in queries:
        context = await memory_system.get_relevant_context(query, limit=2)
        print(f"   Запрос '{query}': найдено {len(context)} релевантных взаимодействий")

        if context:
            for item in context[:1]:  # Показываем только первое
                if item["type"] == "conversation":
                    conv = item["data"]
                    print(f"     - Пользователь: {conv['user_input'][:40]}...")
                    print(f"     - Робот: {conv['robot_response'][:60]}...")

    # Тестируем поиск по памяти
    print("\n🔎 Тестируем поиск по памяти...")
    search_results = await memory_system.search_memories("шутка")
    print(f"   Поиск 'шутка': найдено {len(search_results)} результатов")

    # Тестируем статистику
    print("\n📊 Тестируем статистику памяти...")
    stats = await memory_system.get_memory_stats()
    print(f"   Всего разговоров: {stats['total_conversations']}")
    print(f"   Всего знаний: {stats['total_knowledge_entries']}")
    print(f"   Средний рейтинг успеха: {stats['avg_success_rate']:.2f}")
    print(f"   Использование памяти: {stats['memory_usage_mb']:.2f} MB")

    # Тестируем историю разговоров
    print("\n📜 Тестируем историю разговоров...")
    history = await memory_system.get_conversation_history(limit=3)
    print(f"   Получено {len(history)} последних разговоров")
    for i, conv in enumerate(history):
        print(f"   {i+1}. {conv.user_input[:30]}... → {conv.robot_response[:40]}...")

    # Сохраняем данные
    memory_system.save_data()
    print("💾 Данные сохранены")

    print("\n🎉 Тестирование системы памяти завершено успешно!")
    print("\n🚀 RobotEva теперь имеет:")
    print("   🧠 Долгосрочную память всех взаимодействий")
    print("   📚 Накопление знаний из опыта")
    print("   🔍 Поиск релевантного контекста")
    print("   📊 Статистику и аналитику памяти")
    print("   🎯 Улучшение ответов на основе истории!")


if __name__ == "__main__":
    asyncio.run(test_memory_system())