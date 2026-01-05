#!/usr/bin/env python3
"""
Сброс всех сервоприводов в позицию 0°
"""

import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.config import Config
from robot_eva.hardware.servos import create_servo_controller

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def reset_to_zero():
    print("\n" + "="*60)
    print("🔄 СБРОС СЕРВОПРИВОДОВ В ПОЗИЦИЮ 0°")
    print("="*60)
    
    config = Config("config.yaml")
    servo = create_servo_controller(config)
    
    print("\n📡 Инициализация...")
    await servo.initialize()
    
    if servo.kit is None:
        print("❌ Сервоконтроллер не инициализирован!")
        return
    
    print("✅ Контроллер инициализирован\n")
    
    # Сброс всех каналов в 0°
    channels = [
        (0, "Канал 0: Голова вверх/вниз"),
        (1, "Канал 1: Правая рука"),
        (2, "Канал 2: Голова влево/вправо"),
        (3, "Канал 3: Левая рука"),
    ]
    
    for channel, name in channels:
        print(f"  ➡️  {name} → 0°...", end='', flush=True)
        await servo.move_smooth(channel, 0, steps=15, delay=0.03)
        print(" ✅")
        await asyncio.sleep(0.3)
    
    print("\n" + "="*60)
    print("✅ ВСЕ СЕРВОПРИВОДЫ В ПОЗИЦИИ 0°")
    print("="*60)
    print("\nДефолтные позиции:")
    print("  • Канал 0 (Голова вверх/вниз): 0°")
    print("  • Канал 1 (Правая рука): 0°")
    print("  • Канал 2 (Голова влево/вправо): 0°")
    print("  • Канал 3 (Левая рука): 0°\n")
    
    await servo.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(reset_to_zero())
    except KeyboardInterrupt:
        print("\n⚠️  Прервано")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

