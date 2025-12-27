#!/usr/bin/env python3
"""
Точка входа для робота Eva
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, str(Path(__file__).parent))

from robot_eva.core.robot import RobotEva


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robot_eva.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class RobotController:
    """Контроллер для управления роботом"""
    
    def __init__(self):
        self.robot = None
        self.loop = None
    
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов для корректного завершения"""
        def signal_handler(sig, frame):
            logger.info("Получен сигнал завершения, останавливаем робота...")
            if self.robot:
                asyncio.create_task(self.robot.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Запуск робота"""
        try:
            # Создание экземпляра робота
            config_path = Path(__file__).parent / "config.yaml"
            self.robot = RobotEva(str(config_path) if config_path.exists() else None)
            
            # Инициализация
            logger.info("Инициализация робота Eva...")
            await self.robot.initialize()
            
            # Запуск
            logger.info("Запуск робота Eva...")
            await self.robot.start()
            
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
        finally:
            if self.robot:
                await self.robot.stop()
            logger.info("Робот Eva остановлен")


def main():
    """Главная функция"""
    controller = RobotController()
    controller.setup_signal_handlers()
    
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(controller.run())
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

