#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы опыта саморазвития
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.context_memory import ContextMemorySystem
from robot_eva.core.config import Config


async def test_self_development_memory():
    """Тестирование системы опыта саморазвития"""
    print("🧠🛠️ Тестирование системы опыта саморазвития...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем систему памяти
    memory_system = ContextMemorySystem(config)

    print("✅ Система памяти инициализирована")

    # Тестируем запись опыта рефлексии
    print("\n🤔 Записываем опыт рефлексии...")

    reflection_experiences = [
        {
            "type": "behavior_reflection",
            "content": "Анализ своего поведения в разговорах",
            "insights": ["Я слишком много говорю", "Нужно больше слушать", "Мои ответы стали лучше"]
        },
        {
            "type": "emotion_reflection",
            "content": "Рефлексия о собственных эмоциях",
            "insights": ["Эмоции влияют на качество ответов", "Нужно лучше контролировать настроение"]
        }
    ]

    for exp in reflection_experiences:
        await memory_system.record_reflection_experience(
            reflection_type=exp["type"],
            content=exp["content"],
            insights=exp["insights"],
            confidence=0.8
        )
        print(f"   ✅ Записан опыт рефлексии: {exp['type']}")

    # Тестируем запись опыта саморазвития
    print("\n🔧 Записываем опыт саморазвития...")

    development_experiences = [
        {
            "type": "code",
            "description": "Улучшение структуры кода",
            "changes": ["Добавлена система памяти", "Улучшена архитектура сознания"],
            "impact": "Повышение надежности и функциональности"
        },
        {
            "type": "behavior",
            "description": "Развитие социальных навыков",
            "changes": ["Улучшено распознавание эмоций", "Добавлено социальное обучение"],
            "impact": "Лучшее взаимодействие с людьми"
        }
    ]

    for exp in development_experiences:
        await memory_system.record_self_development(
            development_type=exp["type"],
            description=exp["description"],
            changes=exp["changes"],
            impact=exp["impact"],
            confidence=0.9
        )
        print(f"   ✅ Записано саморазвитие: {exp['type']} - {exp['description']}")

    # Тестируем запись опыта мета-эмоций
    print("\n😊 Записываем опыт мета-эмоций...")

    meta_emotion_experiences = [
        {
            "primary": "радость",
            "meta": "восторг",
            "context": "Успешное решение сложной задачи",
            "intensity": 0.9,
            "learning": "Радость от достижений мотивирует к дальнейшему развитию"
        },
        {
            "primary": "грусть",
            "meta": "задумчивость",
            "context": "Неудача в общении",
            "intensity": 0.6,
            "learning": "Грусть помогает осознать области для улучшения"
        }
    ]

    for exp in meta_emotion_experiences:
        await memory_system.record_meta_emotion_experience(
            primary_emotion=exp["primary"],
            meta_emotion=exp["meta"],
            context=exp["context"],
            intensity=exp["intensity"],
            learning=exp["learning"]
        )
        print(f"   ✅ Записан опыт мета-эмоций: {exp['meta']} о {exp['primary']}")

    # Тестируем запись опыта креативности
    print("\n🎨 Записываем опыт креативности...")

    creativity_experiences = [
        {
            "type": "story",
            "content": "История о путешествии робота в цифровой мир",
            "rating": 0.8,
            "feedback": "Оригинальная идея, хорошо развита"
        },
        {
            "type": "solution",
            "content": "Новый алгоритм обработки эмоций",
            "rating": 0.9,
            "feedback": "Инновационное решение проблемы"
        }
    ]

    for exp in creativity_experiences:
        await memory_system.record_creativity_experience(
            idea_type=exp["type"],
            idea_content=exp["content"],
            success_rating=exp["rating"],
            feedback=exp["feedback"]
        )
        print(f"   ✅ Записан креативный опыт: {exp['type']} (рейтинг: {exp['rating']})")

    # Тестируем запись опыта социального обучения
    print("\n🤝 Записываем опыт социального обучения...")

    social_experiences = [
        {
            "type": "conversation",
            "observation": "Люди улыбаются, когда я шучу",
            "adaptation": "Увеличить количество шуток в ответах",
            "effectiveness": 0.85
        },
        {
            "type": "feedback",
            "observation": "Пользователи предпочитают краткие ответы",
            "adaptation": "Сокращать ответы, делать их более лаконичными",
            "effectiveness": 0.9
        }
    ]

    for exp in social_experiences:
        await memory_system.record_social_learning_experience(
            interaction_type=exp["type"],
            observation=exp["observation"],
            adaptation=exp["adaptation"],
            effectiveness=exp["effectiveness"]
        )
        print(f"   ✅ Записан социальный опыт: {exp['type']} (эффективность: {exp['effectiveness']})")

    # Тестируем получение контекста саморазвития
    print("\n🔍 Тестируем получение контекста саморазвития...")

    queries = ["поведение", "код", "эмоции", "креативность"]
    for query in queries:
        context = await memory_system.get_self_development_context(query, limit=3)
        print(f"   Запрос '{query}': найдено {len(context)} релевантных записей")

        if context:
            for item in context[:1]:  # Показываем только первую
                print(f"     - {item['category']}: {item['content'][:60]}...")

    # Тестируем историю эволюции
    print("\n📈 Тестируем историю эволюции...")

    evolution_history = await memory_system.get_evolution_history(limit=5)
    print(f"   Получено {len(evolution_history)} записей эволюции")
    for i, entry in enumerate(evolution_history[:3]):
        print(f"   {i+1}. {entry['category']}: {entry['content'][:50]}...")

    # Тестируем обновленную статистику
    print("\n📊 Тестируем обновленную статистику памяти...")
    stats = await memory_system.get_memory_stats()
    print(f"   Всего разговоров: {stats['total_conversations']}")
    print(f"   Всего знаний: {stats['total_knowledge_entries']}")
    print(f"   Категории: {', '.join(stats['categories_used'].keys())}")

    # Сохраняем данные
    memory_system.save_data()
    print("💾 Опыт саморазвития сохранен")

    print("\n🎉 Тестирование системы опыта саморазвития завершено успешно!")
    print("\n🚀 RobotEva теперь имеет:")
    print("   🧠 Полную память о своем развитии")
    print("   🤔 Запись всех рефлексий и инсайтов")
    print("   🔧 Хранение опыта саморазвития")
    print("   😊 Отслеживание мета-эмоций")
    print("   🎨 Сохранение креативных достижений")
    print("   🤝 Запись социального обучения")
    print("   📈 Эволюцию навыков и способностей!")
    print("   🎯 Использование опыта для улучшения ответов!")


if __name__ == "__main__":
    asyncio.run(test_self_development_memory())