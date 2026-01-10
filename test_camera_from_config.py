#!/usr/bin/env python3
"""
Тест камеры с использованием настроек из config.yaml
"""

import yaml
import sys

try:
    from picamera2 import Picamera2
    from libcamera import Transform
    import cv2
except ImportError as e:
    print(f"Error: Missing package: {e}")
    print("Install: sudo apt install -y python3-picamera2 python3-opencv")
    sys.exit(1)

# Читаем config.yaml
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

camera_config = config['hardware']['camera']
cam_type = camera_config.get('type', 'usb')
resolution = tuple(camera_config.get('resolution', [640, 480]))
fps = camera_config.get('fps', 30)
rotation = camera_config.get('rotation', 0)

print(f"\n{'='*60}")
print(f"Тест камеры с настройками из config.yaml")
print(f"{'='*60}")
print(f"Тип: {cam_type}")
print(f"Разрешение: {resolution[0]}x{resolution[1]}")
print(f"FPS: {fps}")
print(f"Поворот: {rotation}°")
print(f"{'='*60}\n")

if cam_type != 'csi':
    print("Error: config.yaml настроен на тип камеры 'usb', а не 'csi'")
    print("Измените: hardware.camera.type: csi")
    sys.exit(1)

try:
    # Инициализация
    print("Инициализация камеры...")
    picam2 = Picamera2()
    
    # Трансформация для поворота
    transform = None
    if rotation != 0:
        transform = Transform()
        if rotation == 180:
            transform.hflip = 1
            transform.vflip = 1
        elif rotation == 90:
            transform.vflip = 1
        elif rotation == 270:
            transform.hflip = 1
    
    # Конфигурация
    config_dict = {
        "main": {"size": resolution, "format": "RGB888"},
        "controls": {"FrameRate": fps}
    }
    if transform is not None:
        config_dict["transform"] = transform
    
    cam_config = picam2.create_still_configuration(**config_dict)
    picam2.configure(cam_config)
    picam2.start()
    
    print("Камера запущена!")
    print("Захват кадра...")
    
    # Захват
    frame = picam2.capture_array()
    
    # Конвертация в BGR для OpenCV
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Сохранение
    output_file = "тест_из_конфига.jpg"
    cv2.imwrite(output_file, frame_bgr)
    
    print(f"✅ Снимок сохранён: {output_file}")
    print(f"   Разрешение: {frame.shape[1]}x{frame.shape[0]}")
    print(f"   Поворот применён: {rotation}°")
    
    # Остановка
    picam2.stop()
    picam2.close()
    
    print("\n" + "="*60)
    print("Тест завершён успешно!")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
