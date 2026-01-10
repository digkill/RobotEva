#!/usr/bin/env python3
"""
Тест touch анимаций для RobotEva

Запускает окно с лицом робота. При клике мышью показывает случайную touch анимацию.
Полезно для тестирования анимаций без запуска всего робота.
"""

import asyncio
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robot_eva.core.config import Config
from robot_eva.hardware.display import DisplayManager


async def test_touch_animations():
    """Тестирование touch анимаций"""
    print("=" * 70)
    print("🤖 ТЕСТ TOUCH АНИМАЦИЙ ROBOTEVA")
    print("=" * 70)
    
    # Загрузка конфигурации
    config = Config()
    print("✓ Конфигурация загружена")
    
    # Проверка backend
    backend = config.get("hardware.display.small.backend", "auto")
    print(f"✓ Display backend: {backend}")
    
    if backend == "fbdev":
        print("⚠️  ВНИМАНИЕ: backend=fbdev не поддерживает touch!")
        print("   Установите backend: sdl в config.yaml")
        return
    
    # Проверка touch настроек
    touch_enabled = config.get("hardware.display.small.touch.enabled", True)
    touch_animations = config.get("hardware.display.small.touch.animations", [])
    
    print(f"✓ Touch enabled: {touch_enabled}")
    print(f"✓ Touch animations: {len(touch_animations) if touch_animations else 'all (10)'}")
    
    if touch_animations:
        print(f"  Animations: {', '.join(touch_animations)}")
    else:
        print("  Animations: dizzy, stars, hearts, silly, crazy, sparkle, laugh, blush, surprise_big, money")
    
    # Создание DisplayManager
    display = DisplayManager(config)
    
    try:
        print("\n🚀 Инициализация дисплея...")
        await display.initialize()
        print("✓ Дисплей инициализирован")
        
        # Показываем нейтральное лицо
        print("\n😐 Показываем нейтральное лицо...")
        await display.show_animation("neutral")
        
        print("\n" + "=" * 70)
        print("🖱️  ТЕСТ ГОТОВ!")
        print("=" * 70)
        print("\nИнструкции:")
        print("  • Кликайте по окну мышью (или касайтесь тачскрина)")
        print("  • При каждом клике будет показана случайная touch анимация")
        print("  • Нажмите Ctrl+C для выхода")
        print("\n" + "=" * 70)
        
        # Ждём бесконечно (обработка touch идёт в фоне)
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Остановка...")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🧹 Очистка...")
        await display.cleanup()
        print("✓ Завершено")


def main():
    """Главная функция"""
    try:
        asyncio.run(test_touch_animations())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
