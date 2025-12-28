#!/usr/bin/env python3
"""
Скрипт для проверки маппинга GPIO и устройств
"""
import sys
import os
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent.parent))

from robot_eva.core.config import Config
import yaml


def check_gpio_mapping():
    """Проверка маппинга GPIO"""
    print("=" * 60)
    print("Проверка маппинга GPIO и устройств")
    print("=" * 60)
    print()
    
    config = Config()
    gpio_mapping = config.get_gpio_mapping()
    
    if not gpio_mapping:
        print("❌ Файл gpio_mapping.yaml не найден или пуст")
        return False
    
    print("✓ Файл gpio_mapping.yaml загружен")
    print()
    
    # Проверка I2C устройств
    print("I2C устройства:")
    print("-" * 60)
    i2c_devices = gpio_mapping.get("i2c", {})
    for device_name, device_config in i2c_devices.items():
        enabled = device_config.get("enabled", False)
        address = device_config.get("address", "N/A")
        description = device_config.get("description", "")
        status = "✓" if enabled else "✗"
        print(f"  {status} {device_name}: адрес 0x{address:02X} - {description}")
    print()
    
    # Проверка сервоприводов
    print("Сервоприводы:")
    print("-" * 60)
    servos = gpio_mapping.get("servos", {})
    for servo_name, servo_config in servos.items():
        channel = servo_config.get("channel", "N/A")
        description = servo_config.get("description", "")
        print(f"  ✓ {servo_name}: канал {channel} - {description}")
    print()
    
    # Проверка последовательных портов
    print("Последовательные порты:")
    print("-" * 60)
    serial_devices = gpio_mapping.get("serial", {})
    for device_name, device_config in serial_devices.items():
        enabled = device_config.get("enabled", False)
        port = device_config.get("port", "N/A")
        description = device_config.get("description", "")
        status = "✓" if enabled else "✗"
        exists = "✓" if os.path.exists(port) else "✗"
        print(f"  {status} {device_name}: {port} {exists} - {description}")
    print()
    
    # Проверка USB устройств
    print("USB устройства:")
    print("-" * 60)
    usb_devices = gpio_mapping.get("usb", {})
    for device_name, device_config in usb_devices.items():
        enabled = device_config.get("enabled", False)
        description = device_config.get("description", "")
        status = "✓" if enabled else "✗"
        print(f"  {status} {device_name} - {description}")
    print()
    
    # Проверка реальных I2C устройств
    print("Обнаруженные I2C устройства:")
    print("-" * 60)
    try:
        import subprocess
        result = subprocess.run(
            ["i2cdetect", "-y", "1"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:
                    print(f"  {line}")
            else:
                print("  Нет обнаруженных устройств")
        else:
            print("  Ошибка при выполнении i2cdetect")
    except FileNotFoundError:
        print("  i2cdetect не найден (установите i2c-tools)")
    except Exception as e:
        print(f"  Ошибка: {e}")
    print()
    
    # Проверка последовательных портов
    print("Доступные последовательные порты:")
    print("-" * 60)
    import glob
    serial_ports = glob.glob("/dev/tty*")
    for port in sorted(serial_ports):
        if any(x in port for x in ["USB", "ACM", "AMA"]):
            exists = "✓" if os.path.exists(port) else "✗"
            print(f"  {exists} {port}")
    print()
    
    print("=" * 60)
    print("Проверка завершена")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        check_gpio_mapping()
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

