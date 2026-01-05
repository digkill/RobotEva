#!/usr/bin/env python3
"""
Проверка статуса дисплея в работающем роботе
"""
import sys
import os

# Добавляем путь к модулям робота
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from robot_eva.core.config import Config
from robot_eva.hardware.display import DisplayManager

async def check_display():
    print("=" * 60)
    print("Проверка инициализации DisplayManager")
    print("=" * 60)
    
    # Загружаем конфигурацию
    config = Config("config.yaml")
    
    print(f"\n📋 Конфигурация:")
    print(f"  - small.enabled: {config.get('hardware.display.small.enabled')}")
    print(f"  - small.backend: {config.get('hardware.display.small.backend')}")
    print(f"  - small.size: {config.get('hardware.display.small.size')}")
    print(f"  - small.rotation: {config.get('hardware.display.small.rotation')}")
    print(f"  - small.fbdev: {config.get('hardware.display.small.fbdev')}")
    
    # Проверяем переменные окружения
    print(f"\n🖥️ Переменные окружения:")
    print(f"  - DISPLAY: {os.environ.get('DISPLAY', 'не установлена')}")
    print(f"  - WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', 'не установлена')}")
    
    # Создаем DisplayManager
    print(f"\n🔧 Создание DisplayManager...")
    dm = DisplayManager(config)
    
    try:
        print("📡 Инициализация дисплея...")
        await dm.initialize()
        
        if dm.small_display:
            print("✅ 2.8\" дисплей успешно инициализирован!")
            print(f"   Тип: {type(dm.small_display).__name__}")
        else:
            print("❌ 2.8\" дисплей не инициализирован (small_display = None)")
            return False
        
        # Пробуем показать анимацию
        print("\n🎨 Запуск анимации 'happy'...")
        await dm.show_animation("happy")
        
        # Ждем 3 секунды, чтобы анимация отобразилась
        print("⏳ Ожидание 3 секунды...")
        await asyncio.sleep(3)
        
        if dm.animation_task and not dm.animation_task.done():
            print("✅ Анимация запущена и работает!")
        else:
            print("⚠️ Задача анимации не запущена или завершилась")
            
        # Останавливаем анимацию
        if dm.animation_task:
            dm.animation_task.cancel()
            try:
                await dm.animation_task
            except asyncio.CancelledError:
                pass
        
        print("\n✅ Тест завершен успешно!")
        print("   Если вы НЕ видите лицо на дисплее - проблема может быть в:")
        print("   1. Драйвере дисплея (проверьте dtoverlay в /boot/config.txt)")
        print("   2. Подключении дисплея к DSI-0")
        print("   3. Питании дисплея")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_display())
    sys.exit(0 if success else 1)

