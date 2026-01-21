#!/usr/bin/env python3
"""
Тестовый скрипт для проверки поиска по лицам
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.services.internet import InternetService
from robot_eva.core.config import Config


async def test_face_search():
    """Тестирование поиска по лицам"""
    print("🧪 Тестирование поиска по лицам...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем сервис
    internet_service = InternetService(config)
    await internet_service.initialize()

    print("✅ Сервис интернет-поиска инициализирован")

    # Создаем тестовое изображение (просто белый квадрат)
    import cv2
    import numpy as np

    # Создаем тестовое изображение с "лицом"
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[25:75, 25:75] = [100, 150, 200]  # Серый квадрат как "лицо"

    # Конвертируем в JPEG
    _, buffer = cv2.imencode('.jpg', img)
    image_data = buffer.tobytes()

    print(f"📸 Создали тестовое изображение ({len(image_data)} байт)")

    # Тестируем поиск
    try:
        results = await internet_service.reverse_image_search(image_data, "google")
        print(f"🔍 Найдено результатов: {len(results)}")

        for i, result in enumerate(results[:3]):  # Показываем первые 3 результата
            print(f"  {i+1}. {result.get('title', 'Без названия')}")
            print(f"     {result.get('snippet', 'Без описания')[:100]}...")
            print(f"     {result.get('link', 'Без ссылки')}")

    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")

    print("✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(test_face_search())