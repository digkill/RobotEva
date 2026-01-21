#!/usr/bin/env python3
"""
Тестовый скрипт для проверки автономного поведения робота
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


async def test_autonomous_behavior():
    """Тестирование автономного поведения"""
    print("🤖 Тестирование автономного поведения...")

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
    print("✅ Контейнер инициализирован")

    # Имитируем некоторые наблюдения
    print("\n📊 Создаем тестовые наблюдения...")
    test_observations = [
        {
            "timestamp": asyncio.get_event_loop().time(),
            "sensors": {"presence": {"human_detected": True}},
            "camera": "Вижу человека в комнате",
            "interactions": {"is_listening": False, "is_speaking": False, "is_active": True}
        },
        {
            "timestamp": asyncio.get_event_loop().time() + 10,
            "sensors": {"presence": {"human_detected": False}},
            "camera": None,
            "interactions": {"is_listening": False, "is_speaking": False, "is_active": False}
        }
    ]

    consciousness.observations.extend(test_observations)
    print(f"   Добавлено {len(test_observations)} наблюдений")

    # Тестируем уровень любопытства
    print(f"\n🔍 Уровень любопытства: {consciousness.curiosity_level}")

    # Имитируем одиночество (долгое время без взаимодействия)
    consciousness._last_interaction_ts = asyncio.get_event_loop().time() - 2000  # 33 минуты назад
    await consciousness._update_curiosity_level()
    print(f"   После долгого ожидания: {consciousness.curiosity_level}")

    # Тестируем генерацию автономных эмоций
    print("\n🎭 Тестируем генерацию автономных эмоций...")
    await consciousness._generate_autonomous_emotion()

    # Проверяем состояние
    state = consciousness.get_consciousness_state()
    print(f"📈 Текущее состояние сознания:")
    print(f"   Осознанность: {state['awareness_level']:.1%}")
    print(f"   Наблюдений: {state['observations_count']}")
    print(f"   Любопытство: {consciousness.curiosity_level:.1f}")

    # Тестируем остановку
    await consciousness.stop()
    print("✅ Контейнер остановлен")

    print("\n✅ Тест автономного поведения завершен")


if __name__ == "__main__":
    asyncio.run(test_autonomous_behavior())