#!/usr/bin/env python3
"""
Быстрый тест движений сервоприводов
Проверка работы каналов и плавности движений
"""

import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.config import Config
from robot_eva.hardware.servos import create_servo_controller

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def test_servos():
    print("\n" + "="*60)
    print("🤖 БЫСТРЫЙ ТЕСТ СЕРВОПРИВОДОВ")
    print("="*60)
    
    config = Config("config.yaml")
    servo = create_servo_controller(config)
    
    print("\n📡 Инициализация контроллера...")
    await servo.initialize()
    
    if servo.kit is None:
        print("❌ Сервоконтроллер не инициализирован!")
        print("   Проверьте: i2cdetect -y 1")
        return
    
    print("✅ Контроллер инициализирован\n")
    
    # Определяем тесты (дефолт позиция 0°)
    tests = [
        ("Канал 0: Голова вверх/вниз", 0, [0, 45, 90, 45, 0]),
        ("Канал 1: Правая рука", 1, [0, 45, 90, 45, 0]),
        ("Канал 2: Голова влево/вправо", 2, [0, 45, 90, 45, 0]),
        ("Канал 3: Левая рука", 3, [0, 45, 90, 45, 0]),
    ]
    
    for name, channel, angles in tests:
        print(f"{'─'*60}")
        print(f"🔧 Тест: {name}")
        print(f"{'─'*60}")
        
        for angle in angles:
            print(f"  ➡️  Плавное движение на {angle}°...", end='', flush=True)
            await servo.move_smooth(channel, angle, steps=15, delay=0.02)
            print(" ✅")
            await asyncio.sleep(0.5)
        
        print()
    
    print("="*60)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("="*60)
    print("\n📋 Проверьте:")
    print("   ✓ Все сервоприводы плавно двигаются")
    print("   ✓ Нет рывков и дрожания")
    print("   ✓ Движения не упираются в механические ограничения")
    print("\n💡 Для точной калибровки запустите: python calibrate_servos.py\n")
    
    await servo.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(test_servos())
    except KeyboardInterrupt:
        print("\n⚠️  Прервано")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

