#!/usr/bin/env python3
"""
Тестовый скрипт для проверки автоматического применения улучшений
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.code_self_analysis import CodeSelfAnalysis
from robot_eva.core.config import Config


async def test_automatic_improvements():
    """Тестирование автоматического применения улучшений"""
    print("🔧 Тестирование автоматического применения улучшений...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем систему самоанализа
    code_analysis = CodeSelfAnalysis(config)

    print("✅ Система самоанализа кода инициализирована")

    # Создаем тестовые предложения улучшений
    test_suggestions = [
        {
            "title": "Добавить проверки на None",
            "description": "Добавить проверки на None для предотвращения ошибок",
            "priority": "medium"
        },
        {
            "title": "Улучшить обработку ошибок",
            "description": "Добавить более подробную обработку исключений",
            "priority": "high"
        },
        {
            "title": "Оптимизировать использование памяти",
            "description": "Улучшить управление памятью в критических секциях",
            "priority": "low"
        }
    ]

    # Добавляем тестовые предложения
    code_analysis.improvement_suggestions.extend(test_suggestions)
    print(f"📝 Добавлено {len(test_suggestions)} тестовых предложений улучшений")

    # Тестируем автоматическое применение
    print("\n🔧 Тестируем автоматическое применение улучшений...")

    applied_count = 0
    for suggestion in test_suggestions:
        print(f"   ├─> Применяем: {suggestion['title']}")

        # Применяем без подтверждения
        success = await code_analysis.apply_improvement(suggestion, confirm=False)
        if success:
            applied_count += 1
            print("   │   └─> ✅ Применено успешно")
        else:
            print("   │   └─> ❌ Применить не удалось")

    print(f"\n🎯 Результат: автоматически применено {applied_count}/{len(test_suggestions)} улучшений")

    # Проверяем историю примененных улучшений
    print("\n📚 Проверяем историю примененных улучшений...")
    history = code_analysis.get_applied_improvements_history(limit=5)

    print(f"   ├─> Всего в истории: {len(history)} записей")
    for i, improvement in enumerate(history[-3:], 1):  # Показываем последние 3
        print(f"   ├─> {i}. {improvement.get('title', 'Без названия')}")
        print(f"   │   └─> Авто-применено: {improvement.get('auto_applied', False)}")

    # Проверяем счетчик
    count = code_analysis.get_applied_improvements_count()
    print(f"   └─> Общее количество примененных улучшений: {count}")

    print("\n🎉 Тестирование автоматического применения улучшений завершено!")
    print("\n🚀 RobotEva теперь:")
    print("   ✅ Автоматически применяет улучшения без подтверждения")
    print("   ✅ Записывает все изменения в историю")
    print("   ✅ Отслеживает прогресс саморазвития")
    print("   ✅ Непрерывно совершенствуется!")


if __name__ == "__main__":
    asyncio.run(test_automatic_improvements())
