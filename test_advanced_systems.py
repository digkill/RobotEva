#!/usr/bin/env python3
"""
Тестовый скрипт для проверки продвинутых систем RobotEva
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.consciousness import ConsciousnessContainer
from robot_eva.core.config import Config


class MockRobot:
    """Мок-объект для тестирования сознания"""
    def __init__(self):
        self.llm_service = None
        self.text_to_speech = None
        self.camera_manager = None
        self.emotion_engine = None
        self.display_manager = None
        self.sensor_manager = None


async def test_advanced_systems():
    """Тестирование продвинутых систем"""
    print("🧠🤖 Тестирование продвинутых систем RobotEva...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем мок-робота
    robot = MockRobot()

    # Создаем контейнер сознания
    consciousness = ConsciousnessContainer(config, robot)

    print("✅ Контейнер сознания создан")

    # Тестируем инициализацию
    await consciousness.initialize()
    print("✅ Продвинутые системы инициализированы")

    # Имитируем некоторые наблюдения
    test_observations = [
        {
            "timestamp": asyncio.get_event_loop().time(),
            "sensors": {"presence": {"human_detected": True}},
            "camera": "Вижу человека улыбающегося",
            "interactions": {"is_listening": False, "is_speaking": False, "is_active": True}
        },
        {
            "timestamp": asyncio.get_event_loop().time() + 5,
            "sensors": {"presence": {"human_detected": True}},
            "camera": "Человек машет рукой",
            "interactions": {"is_listening": True, "is_speaking": False, "is_active": True}
        }
    ]

    consciousness.observations.extend(test_observations)
    print(f"   Добавлено {len(test_observations)} наблюдений")

    # Тестируем социальное обучение
    print("\n👥 Тестируем социальное обучение...")
    await consciousness.social_learning.record_interaction(
        person_id="test_user",
        action="waving",
        context={"emotion": "happy", "type": "gesture"}
    )
    print("   ✅ Взаимодействие записано")

    # Тестируем мета-эмоции
    print("\n🎭 Тестируем мета-эмоции...")
    await consciousness.meta_emotions.record_emotion(
        emotion="happy",
        intensity=0.8,
        valence=0.9,
        arousal=0.7,
        context={"reason": "social_interaction"},
        trigger="user_waved"
    )
    print("   ✅ Эмоция записана")

    # Тестируем креативность (без LLM)
    print("\n🎨 Тестируем креативность...")
    # Создаем тестовую идею вручную
    from robot_eva.core.creativity import CreativeIdea
    test_idea = CreativeIdea(
        id="test_idea_001",
        timestamp=asyncio.get_event_loop().time(),
        category="story",
        prompt="Тестовая история",
        content="Это тестовая креативная идея для проверки системы.",
        quality_score=0.8,
        originality=0.7,
        usefulness=0.6,
        tags=["test", "creativity"],
        context={}
    )
    consciousness.creativity.ideas[test_idea.id] = test_idea
    print("   ✅ Идея создана")

    # Проверяем состояние
    state = consciousness.get_consciousness_state()
    print("\n📊 Состояние продвинутых систем:")
    print(f"   Социальное обучение: {state['social_learning']['total_interactions']} взаимодействий")
    print(f"   Мета-эмоции: {state['meta_emotions']['total_emotions']} эмоций")
    print(f"   Креативность: {state['creativity']['total_ideas']} идей")
    print(f"   Коллективный интеллект: {state['collective_intelligence']['enabled']}")

    # Тестируем коллективный интеллект
    print("\n🌐 Тестируем коллективный интеллект...")
    collective_stats = consciousness.collective_intelligence.get_collective_stats()
    print(f"   Робот ID: {collective_stats['robot_id']}")
    print(f"   Активен: {collective_stats['enabled']}")
    print(f"   Знаний: {collective_stats['knowledge_packets']}")

    # Тестируем завершение
    await consciousness.stop()
    print("✅ Все системы остановлены")

    print("\n🎉 Тестирование продвинутых систем завершено успешно!")
    print("\n🚀 RobotEva теперь имеет:")
    print("   🧠 Продвинутое сознание с самоанализом")
    print("   👥 Социальное обучение и адаптацию")
    print("   🎭 Мета-эмоции второго порядка")
    print("   🎨 Креативность и генерацию идей")
    print("   🌐 Коллективный интеллект")
    print("   🤖 Полную автономную эволюцию!")


if __name__ == "__main__":
    asyncio.run(test_advanced_systems())