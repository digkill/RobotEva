#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы сознания
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


async def test_consciousness():
    """Тестирование системы сознания"""
    print("🧠 Тестирование системы сознания...")

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

    # Тестируем получение состояния
    state = consciousness.get_consciousness_state()
    print("📊 Состояние сознания:")
    print(f"   Активно: {state['is_active']}")
    print(".1f")
    print(f"   Наблюдений: {state['observations_count']}")
    print(f"   Рефлексий: {state['reflections_count']}")

    # Тестируем анализ кода (без LLM)
    print("
🔍 Тестируем анализ кода...")
    try:
        analysis_result = await consciousness.code_self_analysis.analyze_own_code()
        if analysis_result and "error" not in analysis_result:
            summary = analysis_result.get("summary", {})
            print(f"   Проанализировано файлов: {summary.get('total_files', 0)}")
            print(f"   Всего строк: {summary.get('total_lines', 0)}")
            print(f"   Найдено проблем: {summary.get('issues_count', 0)}")
        else:
            print("   Анализ не выполнен (нет LLM или ошибка)")
    except Exception as e:
        print(f"   Ошибка анализа: {e}")

    # Тестируем остановку
    await consciousness.stop()
    print("✅ Контейнер остановлен")

    print("\n✅ Тест сознания завершен")


if __name__ == "__main__":
    asyncio.run(test_consciousness())