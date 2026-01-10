#!/usr/bin/env python3
"""
Тестовый скрипт для проверки face tracking (отслеживания лица).
Показывает видео с камеры с рамкой вокруг обнаруженного лица и текущие углы сервоприводов.
"""
import asyncio
import sys
import time
import cv2
import numpy as np
from pathlib import Path

# Добавляем путь к модулям проекта
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.config import Config
from robot_eva.hardware.camera import CameraManager


class MockServoController:
    """Mock servo controller для тестирования без реального железа"""
    SERVO_HEAD_YAW = 2
    SERVO_HEAD_PITCH = 0
    
    def __init__(self):
        self.current_yaw = 0.0
        self.current_pitch = 0.0
    
    async def move(self, servo_id, angle):
        if servo_id == self.SERVO_HEAD_YAW:
            self.current_yaw = angle
            print(f"  → YAW: {angle:.1f}°")
        elif servo_id == self.SERVO_HEAD_PITCH:
            self.current_pitch = angle
            print(f"  → PITCH: {angle:.1f}°")
    
    async def move_smooth(self, servo_id, angle, steps=3, delay=0.02):
        await self.move(servo_id, angle)


async def test_face_tracking():
    """Тестирование face tracking с визуализацией"""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║         ТЕСТ FACE TRACKING (Отслеживание лица)                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    # Загружаем конфигурацию
    print("📋 Загрузка конфигурации...")
    config = Config()
    
    # Проверяем настройки face_tracking
    enabled = config.get("behavior.face_tracking.enabled", False)
    fps = config.get("behavior.face_tracking.fps", 8)
    max_yaw = config.get("behavior.face_tracking.max_yaw_deg", 40)
    max_pitch = config.get("behavior.face_tracking.max_pitch_deg", 25)
    
    print(f"   Enabled: {enabled}")
    print(f"   FPS: {fps}")
    print(f"   Max Yaw: {max_yaw}°")
    print(f"   Max Pitch: {max_pitch}°")
    print()
    
    if not enabled:
        print("⚠️  Face tracking отключен в config.yaml!")
        print("   Установите behavior.face_tracking.enabled: true")
        return
    
    # Инициализируем камеру
    print("📹 Инициализация камеры...")
    camera = CameraManager(config)
    await camera.initialize()
    
    if not camera.is_available():
        print("❌ Камера недоступна!")
        return
    
    print("✅ Камера готова!")
    print()
    
    # Инициализируем Mock servo controller
    print("🤖 Инициализация mock servo controller...")
    servos = MockServoController()
    print("✅ Mock servos готовы!")
    print()
    
    # Загружаем Haar Cascade
    print("🔍 Загрузка Haar Cascade для детекции лиц...")
    cascade_path = config.get("behavior.face_tracking.cascade_path", None)
    if not cascade_path:
        # Try local data/ folder first
        import os
        local_cascade = os.path.join(Path(__file__).parent, "data", "haarcascade_frontalface_default.xml")
        if os.path.exists(local_cascade):
            cascade_path = local_cascade
        elif hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            # Fallback to cv2.data if available
            cascade_path = str(cv2.data.haarcascades) + "haarcascade_frontalface_default.xml"
        else:
            # Last resort: assume system path
            cascade_path = "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml"
    
    cascade_path = str(cascade_path)
    cascade = cv2.CascadeClassifier(cascade_path)
    
    if cascade.empty():
        print(f"❌ Не удалось загрузить cascade: {cascade_path}")
        return
    
    print(f"✅ Cascade загружен: {cascade_path}")
    print()
    
    # Параметры детекции
    scale_factor = float(config.get("behavior.face_tracking.scale_factor", 1.2))
    min_neighbors = int(config.get("behavior.face_tracking.min_neighbors", 5))
    min_face_px = int(config.get("behavior.face_tracking.min_face_size_px", 30))
    
    # Параметры движения
    yaw_center = float(config.get("behavior.motion.center.head_yaw", 0))
    pitch_center = float(config.get("behavior.motion.center.neck_pitch", 0))
    smoothing_alpha = float(config.get("behavior.face_tracking.smoothing_alpha", 0.75))
    deadzone = float(config.get("behavior.face_tracking.deadzone", 0.07))
    invert_yaw = bool(config.get("behavior.face_tracking.invert_yaw", False))
    invert_pitch = bool(config.get("behavior.face_tracking.invert_pitch", True))
    
    print("⚙️  Параметры детекции:")
    print(f"   scale_factor: {scale_factor}")
    print(f"   min_neighbors: {min_neighbors}")
    print(f"   min_face_size: {min_face_px}px")
    print()
    
    print("⚙️  Параметры движения:")
    print(f"   yaw_center: {yaw_center}°")
    print(f"   pitch_center: {pitch_center}°")
    print(f"   smoothing_alpha: {smoothing_alpha}")
    print(f"   deadzone: {deadzone}")
    print(f"   invert_yaw: {invert_yaw}")
    print(f"   invert_pitch: {invert_pitch}")
    print()
    
    print("🚀 Запуск face tracking...")
    print("   Нажмите Ctrl+C для выхода")
    print()
    
    # Состояние
    yaw_target = yaw_center
    pitch_target = pitch_center
    interval = 1.0 / fps
    
    frame_count = 0
    last_print_time = time.time()
    
    try:
        while True:
            t0 = time.time()
            
            # Захват кадра
            frame = await camera.capture_frame()
            if frame is None:
                await asyncio.sleep(interval)
                continue
            
            h, w = frame.shape[:2]
            if w < 10 or h < 10:
                await asyncio.sleep(interval)
                continue
            
            # Детекция лиц
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=scale_factor,
                minNeighbors=min_neighbors,
                flags=cv2.CASCADE_SCALE_IMAGE,
                minSize=(min_face_px, min_face_px),
            )
            
            frame_count += 1
            
            # Обработка результата
            if faces is None or len(faces) == 0:
                # Нет лица
                if time.time() - last_print_time >= 2.0:
                    print(f"[{frame_count:04d}] ❌ Лицо не обнаружено")
                    last_print_time = time.time()
            else:
                # Лицо найдено - берём самое большое
                x, y, fw, fh = max(faces, key=lambda r: int(r[2]) * int(r[3]))
                cx = x + fw / 2.0
                cy = y + fh / 2.0
                
                # Нормализованная ошибка (-1..1)
                ex = (cx - (w / 2.0)) / (w / 2.0)
                ey = (cy - (h / 2.0)) / (h / 2.0)
                
                # Deadzone
                if abs(ex) < deadzone:
                    ex = 0.0
                if abs(ey) < deadzone:
                    ey = 0.0
                
                # Инверсия
                if invert_yaw:
                    ex = -ex
                if invert_pitch:
                    ey = -ey
                
                # Вычисляем целевые углы
                yaw_new = yaw_center + (ex * max_yaw)
                pitch_new = pitch_center + (ey * max_pitch)
                
                # Сглаживание
                yaw_target = (smoothing_alpha * yaw_target) + ((1.0 - smoothing_alpha) * yaw_new)
                pitch_target = (smoothing_alpha * pitch_target) + ((1.0 - smoothing_alpha) * pitch_new)
                
                # Движение сервоприводов
                await servos.move(servos.SERVO_HEAD_YAW, yaw_target)
                await servos.move(servos.SERVO_HEAD_PITCH, pitch_target)
                
                # Вывод информации
                print(f"[{frame_count:04d}] ✅ Лицо найдено!")
                print(f"   Позиция: ({int(cx)}, {int(cy)}) | Размер: {fw}x{fh}")
                print(f"   Ошибка: ex={ex:+.2f} ey={ey:+.2f}")
                print(f"   Углы: YAW={yaw_target:.1f}° PITCH={pitch_target:.1f}°")
                print()
                last_print_time = time.time()
            
            # Пауза до следующего кадра
            dt = time.time() - t0
            await asyncio.sleep(max(0.0, interval - dt))
            
    except KeyboardInterrupt:
        print()
        print("⏹️  Остановка...")
    finally:
        print()
        print("📊 Статистика:")
        print(f"   Обработано кадров: {frame_count}")
        print(f"   Последние углы: YAW={servos.current_yaw:.1f}° PITCH={servos.current_pitch:.1f}°")
        print()
        print("✅ Тест завершён!")


if __name__ == "__main__":
    asyncio.run(test_face_tracking())
