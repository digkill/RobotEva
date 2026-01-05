#!/usr/bin/env python3
"""
Тест Face Tracking - проверка работы отслеживания лица
"""

import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.config import Config
from robot_eva.hardware.servos import create_servo_controller
from robot_eva.hardware.camera import CameraManager
from robot_eva.behaviors.face_tracking import FaceTrackingBehavior

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_face_tracking():
    print("\n" + "="*60)
    print("👁️  ТЕСТ FACE TRACKING")
    print("="*60)
    
    config = Config("config.yaml")
    
    # Инициализация компонентов
    print("\n📡 Инициализация компонентов...")
    
    servo = create_servo_controller(config)
    await servo.initialize()
    if servo.kit is None:
        print("❌ Сервоконтроллер не инициализирован!")
        return
    print("✅ Сервоконтроллер")
    
    camera = CameraManager(config)
    await camera.initialize()
    if not camera.is_available():
        print("❌ Камера не доступна!")
        return
    print("✅ Камера")
    
    # Создаем FaceTracking behavior
    face_tracking = FaceTrackingBehavior(config, camera, servo)
    await face_tracking.initialize()
    
    if not face_tracking.enabled:
        print("❌ Face Tracking не включен или не инициализирован!")
        return
    print("✅ Face Tracking инициализирован")
    
    # Показываем конфигурацию
    print("\n📋 Конфигурация:")
    print(f"  • Канал Head Yaw (повороты): {servo.SERVO_HEAD_YAW}")
    print(f"  • Канал Head Pitch (кивки): {servo.SERVO_HEAD_PITCH}")
    print(f"  • Центр Yaw: {config.get('behavior.motion.center.head_yaw', 0)}°")
    print(f"  • Центр Pitch: {config.get('behavior.motion.center.neck_pitch', 0)}°")
    print(f"  • Max Yaw: ±{config.get('behavior.face_tracking.max_yaw_deg', 40)}°")
    print(f"  • Max Pitch: ±{config.get('behavior.face_tracking.max_pitch_deg', 25)}°")
    print(f"  • Smooth steps: {config.get('behavior.face_tracking.smooth_steps', 8)}")
    print(f"  • Invert Yaw: {config.get('behavior.face_tracking.invert_yaw', False)}")
    print(f"  • Invert Pitch: {config.get('behavior.face_tracking.invert_pitch', True)}")
    
    # Сброс в центр
    print("\n🔄 Сброс серв в центр (0°)...")
    await servo.move_smooth(servo.SERVO_HEAD_YAW, 0, steps=10, delay=0.03)
    await servo.move_smooth(servo.SERVO_HEAD_PITCH, 0, steps=10, delay=0.03)
    await asyncio.sleep(1)
    
    # Запуск face tracking
    print("\n🎬 Запуск Face Tracking...")
    print("   Встаньте перед камерой и двигайтесь!")
    print("   Нажмите Ctrl+C для остановки\n")
    
    await face_tracking.start()
    
    try:
        # Работаем 30 секунд или до Ctrl+C
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\n\n⚠️  Остановка...")
    
    # Остановка
    print("\n🛑 Остановка Face Tracking...")
    await face_tracking.stop()
    
    # Возврат в центр
    print("🔄 Возврат серв в центр...")
    await servo.move_smooth(servo.SERVO_HEAD_YAW, 0, steps=10, delay=0.03)
    await servo.move_smooth(servo.SERVO_HEAD_PITCH, 0, steps=10, delay=0.03)
    
    # Очистка
    await camera.cleanup()
    await servo.cleanup()
    
    print("\n" + "="*60)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*60)
    print("\n📋 Проверьте:")
    print("   ✓ Голова поворачивалась за вами влево/вправо")
    print("   ✓ Голова наклонялась вверх/вниз")
    print("   ✓ Движения были плавными")
    print("   ✓ Голова вернулась в центр (0°)")
    print("\n💡 Если что-то не работает:")
    print("   → Прочитайте FACE_TRACKING_FIX.md")
    print("   → Измените invert_yaw/invert_pitch в config.yaml")
    print("   → Настройте max_yaw_deg/max_pitch_deg\n")

if __name__ == "__main__":
    try:
        asyncio.run(test_face_tracking())
    except KeyboardInterrupt:
        print("\n⚠️  Прервано")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

