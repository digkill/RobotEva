#!/usr/bin/env python3
"""
Тестовый скрипт для проверки wake word "Hey Eva"
"""
import asyncio
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.ai.wake_word import WakeWordDetector
from robot_eva.core.config import Config


async def test_wake_word():
    """Тестирование wake word 'Hey Eva'"""
    print("🎤 Тестирование wake word 'Hey Eva'...")

    # Загружаем конфигурацию
    config_path = Path(__file__).parent / "config.yaml"
    config = Config(str(config_path) if config_path.exists() else None)

    # Создаем детектор wake word
    detector = WakeWordDetector(config)

    print("🔧 Инициализация wake word детектора...")

    try:
        await detector.initialize()
        print("✅ Wake word детектор инициализирован")

        # Показываем конфигурацию
        require_wake_up = bool(config.get("ai.wake_word.require_wake_up", False))
        mode = str(config.get("ai.wake_word.openwakeword.mode", "onnx"))
        hey_eva_path = str(config.get("ai.wake_word.openwakeword.hey_eva_onnx_path", ""))

        print("📋 Конфигурация wake word:")
        print(f"   • Требуется 'wake up': {require_wake_up}")
        print(f"   • Режим: {mode}")
        print(f"   • Модель 'Hey Eva': {hey_eva_path}")
        print(f"   • Команда активации: 'Hey Eva' {'wake up' if require_wake_up else ''}")

        print("\n🎧 Слушаю wake word 'Hey Eva'... (скажите 'Hey Eva' в микрофон)")
        print("   Нажмите Ctrl+C для выхода")

        # Слушаем wake word
        while True:
            try:
                detected = await detector.detect()
                if detected:
                    print("🎉 Wake word 'Hey Eva' обнаружен!")
                    if require_wake_up:
                        print("   Теперь скажите 'wake up' для полной активации")
                    else:
                        print("   Робот должен начать слушать команду!")
                    break
                else:
                    print(".", end="", flush=True)
                    await asyncio.sleep(0.1)

            except KeyboardInterrupt:
                print("\n⏹️  Тест прерван пользователем")
                break
            except Exception as e:
                print(f"\n❌ Ошибка при обнаружении wake word: {e}")
                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Ошибка инициализации wake word детектора: {e}")

    finally:
        # Останавливаем детектор
        try:
            await detector.stop_listening()
            print("🛑 Wake word детектор остановлен")
        except Exception:
            pass

    print("\n🎯 Тест завершен!")


if __name__ == "__main__":
    asyncio.run(test_wake_word())