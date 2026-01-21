#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы самоанализа кода
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.code_self_analysis import CodeSelfAnalysis
from robot_eva.core.config import Config


async def test_self_analysis():
    """Тестирование самоанализа кода"""
    print("🧠 Тестирование системы самоанализа кода...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем систему самоанализа
    code_analyzer = CodeSelfAnalysis(config)

    print("✅ Система самоанализа инициализирована")

    # Тестируем поиск файлов
    python_files = code_analyzer._find_python_files()
    print(f"📁 Найдено Python файлов: {len(python_files)}")

    for i, file_path in enumerate(python_files[:5]):  # Показываем первые 5
        print(f"  {i+1}. {file_path.name}")

    if python_files:
        # Тестируем анализ одного файла
        print(f"\n🔍 Анализируем файл: {python_files[0].name}")
        analysis = await code_analyzer._analyze_single_file(python_files[0])

        if analysis:
            print("✅ Анализ завершен:")
            print(f"   Строк кода: {analysis.get('lines', 0)}")
            print(f"   Классов: {len(analysis.get('classes', []))}")
            print(f"   Функций: {len(analysis.get('functions', []))}")
            print(f"   Проблем: {len(analysis.get('issues', []))}")

            # Показываем проблемы
            issues = analysis.get('issues', [])
            if issues:
                print("   Найденные проблемы:")
                for issue in issues[:3]:  # Первые 3 проблемы
                    print(f"     - {issue.get('message', '')}")
        else:
            print("❌ Анализ не удался")

    # Тестируем метрики
    print("\n📊 Тестируем получение метрик...")
    metrics = code_analyzer.get_code_metrics()
    if metrics:
        print(f"   Всего файлов: {metrics.get('total_files', 0)}")
        print(f"   Всего строк: {metrics.get('total_lines', 0)}")
        print(f"   Найденных проблем: {metrics.get('issues_count', 0)}")
    else:
        print("   Метрики недоступны (нужен полный анализ)")

    # Тестируем историю
    history = code_analyzer.get_analysis_history()
    print(f"\n📚 История анализов: {len(history)} записей")

    print("\n✅ Тест самоанализа завершен")


if __name__ == "__main__":
    asyncio.run(test_self_analysis())