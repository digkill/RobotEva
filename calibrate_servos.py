#!/usr/bin/env python3
"""
Калибровка сервоприводов робота Eva
Интерактивный скрипт для настройки диапазонов углов и центральных положений
"""

import sys
import asyncio
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.config import Config
from robot_eva.hardware.servos import create_servo_controller

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ServoCalibrator:
    def __init__(self):
        self.config = Config("config.yaml")
        self.servo_controller = None
        
        # Названия сервоприводов
        self.servo_names = {
            0: "Канал 0: Голова вверх/вниз (Neck Pitch)",
            1: "Канал 1: Правая рука",
            2: "Канал 2: Голова влево/вправо (Head Yaw)",
            3: "Канал 3: Левая рука"
        }
        
    async def initialize(self):
        """Инициализация контроллера"""
        print("\n" + "="*60)
        print("🤖 КАЛИБРОВКА СЕРВОПРИВОДОВ ROBOT EVA")
        print("="*60)
        
        self.servo_controller = create_servo_controller(self.config)
        await self.servo_controller.initialize()
        
        if self.servo_controller.kit is None:
            print("\n❌ ОШИБКА: Сервоконтроллер не инициализирован!")
            print("   Проверьте подключение PCA9685 к I2C")
            print("   Команда для проверки: i2cdetect -y 1")
            return False
            
        print("✅ Сервоконтроллер инициализирован")
        return True
    
    async def test_servo(self, channel, min_angle=30, max_angle=150, center=90):
        """Тестирование одного сервопривода"""
        name = self.servo_names.get(channel, f"Канал {channel}")
        
        print(f"\n{'─'*60}")
        print(f"📍 Тестирование: {name} (Канал {channel})")
        print(f"{'─'*60}")
        
        while True:
            print(f"\n  Текущие настройки:")
            print(f"    Min: {min_angle}°  |  Center: {center}°  |  Max: {max_angle}°")
            print(f"\n  Команды:")
            print(f"    1 - Переместить в центр ({center}°)")
            print(f"    2 - Переместить в минимум ({min_angle}°)")
            print(f"    3 - Переместить в максимум ({max_angle}°)")
            print(f"    4 - Установить свой угол")
            print(f"    5 - Плавное движение (тест)")
            print(f"    c - Изменить центр")
            print(f"    m - Изменить минимум")
            print(f"    x - Изменить максимум")
            print(f"    s - Сохранить настройки")
            print(f"    n - Следующий сервопривод")
            print(f"    q - Выход")
            
            choice = input("\n  Выбор: ").strip().lower()
            
            if choice == '1':
                print(f"  ➡️  Перемещение в центр ({center}°)...")
                await self.servo_controller.move(channel, center)
                await asyncio.sleep(0.5)
                
            elif choice == '2':
                print(f"  ➡️  Перемещение в минимум ({min_angle}°)...")
                await self.servo_controller.move(channel, min_angle)
                await asyncio.sleep(0.5)
                
            elif choice == '3':
                print(f"  ➡️  Перемещение в максимум ({max_angle}°)...")
                await self.servo_controller.move(channel, max_angle)
                await asyncio.sleep(0.5)
                
            elif choice == '4':
                try:
                    angle = float(input("  Введите угол (0-180): "))
                    if 0 <= angle <= 180:
                        print(f"  ➡️  Перемещение на {angle}°...")
                        await self.servo_controller.move(channel, angle)
                        await asyncio.sleep(0.5)
                    else:
                        print("  ⚠️  Угол должен быть от 0 до 180")
                except ValueError:
                    print("  ⚠️  Неверный формат числа")
                    
            elif choice == '5':
                print(f"  🎬 Плавное движение {min_angle}° → {max_angle}° → {center}°...")
                await self.servo_controller.move_smooth(channel, min_angle, steps=15, delay=0.03)
                await asyncio.sleep(0.3)
                await self.servo_controller.move_smooth(channel, max_angle, steps=15, delay=0.03)
                await asyncio.sleep(0.3)
                await self.servo_controller.move_smooth(channel, center, steps=15, delay=0.03)
                
            elif choice == 'c':
                try:
                    new_center = float(input(f"  Новый центр (текущий {center}°): "))
                    if min_angle <= new_center <= max_angle:
                        center = new_center
                        print(f"  ✅ Центр установлен на {center}°")
                    else:
                        print(f"  ⚠️  Центр должен быть между {min_angle}° и {max_angle}°")
                except ValueError:
                    print("  ⚠️  Неверный формат числа")
                    
            elif choice == 'm':
                try:
                    new_min = float(input(f"  Новый минимум (текущий {min_angle}°): "))
                    if 0 <= new_min < max_angle:
                        min_angle = new_min
                        print(f"  ✅ Минимум установлен на {min_angle}°")
                    else:
                        print(f"  ⚠️  Минимум должен быть от 0° и меньше {max_angle}°")
                except ValueError:
                    print("  ⚠️  Неверный формат числа")
                    
            elif choice == 'x':
                try:
                    new_max = float(input(f"  Новый максимум (текущий {max_angle}°): "))
                    if min_angle < new_max <= 180:
                        max_angle = new_max
                        print(f"  ✅ Максимум установлен на {max_angle}°")
                    else:
                        print(f"  ⚠️  Максимум должен быть больше {min_angle}° и до 180°")
                except ValueError:
                    print("  ⚠️  Неверный формат числа")
                    
            elif choice == 's':
                self._save_calibration(channel, min_angle, max_angle, center)
                
            elif choice == 'n':
                # Вернуть в центр перед переходом
                await self.servo_controller.move(channel, center)
                return
                
            elif choice == 'q':
                return 'quit'
                
            else:
                print("  ⚠️  Неверная команда")
    
    def _save_calibration(self, channel, min_angle, max_angle, center):
        """Сохранение калибровки в gpio_mapping.yaml"""
        print(f"\n  💾 Сохранение настроек для канала {channel}...")
        
        # Определяем имя сервопривода
        servo_name_map = {
            2: "head_yaw",
            0: "neck_pitch",
            3: "left_arm",
            1: "right_arm"
        }
        
        servo_name = servo_name_map.get(channel)
        if not servo_name:
            print(f"  ⚠️  Неизвестный канал {channel}")
            return
        
        print(f"\n  Добавьте эти строки в gpio_mapping.yaml:")
        print(f"  {'─'*50}")
        print(f"  {servo_name}:")
        print(f"    channel: {channel}")
        print(f"    min_angle: {int(min_angle)}")
        print(f"    max_angle: {int(max_angle)}")
        print(f"    default_angle: {int(center)}")
        print(f"  {'─'*50}")
        print(f"  ✅ Скопируйте эти значения в файл вручную")
    
    async def run(self):
        """Главный цикл калибровки"""
        if not await self.initialize():
            return
        
        print("\n📝 ИНСТРУКЦИЯ:")
        print("   1. Тестируйте каждый сервопривод")
        print("   2. Найдите безопасные минимум/максимум углы")
        print("   3. Определите центральное положение")
        print("   4. Сохраните настройки")
        print("\n⚠️  ВНИМАНИЕ: Не доводите сервопривод до механических упоров!")
        print("   Оставьте запас ~10° с каждой стороны")
        
        # Порядок калибровки (дефолт позиция 0°)
        channels_to_calibrate = [
            (0, 0, 180, 0),   # Канал 0: Голова вверх/вниз
            (1, 0, 180, 0),   # Канал 1: Правая рука
            (2, 0, 180, 0),   # Канал 2: Голова влево/вправо
            (3, 0, 180, 0),   # Канал 3: Левая рука
        ]
        
        for channel, min_a, max_a, center in channels_to_calibrate:
            result = await self.test_servo(channel, min_a, max_a, center)
            if result == 'quit':
                break
        
        print("\n" + "="*60)
        print("✅ Калибровка завершена!")
        print("="*60)
        print("\nНе забудьте обновить значения в gpio_mapping.yaml")
        
        # Возврат всех сервоприводов в центр
        print("\n🔄 Возврат сервоприводов в центральные положения...")
        for channel, _, _, center in channels_to_calibrate:
            await self.servo_controller.move(channel, center)
            await asyncio.sleep(0.2)
        
        await self.servo_controller.cleanup()

async def main():
    calibrator = ServoCalibrator()
    try:
        await calibrator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

