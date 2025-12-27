"""
Управление LED индикатором (7-цветной мигающий)
"""
import logging
import serial
import asyncio
from typing import Optional


class LEDController:
    """Контроллер LED индикатора"""
    
    # Статусы робота
    STATUS_READY = "ready"
    STATUS_LISTENING = "listening"
    STATUS_THINKING = "thinking"
    STATUS_SPEAKING = "speaking"
    STATUS_ACTIVE = "active"
    STATUS_SLEEP = "sleep"
    STATUS_ERROR = "error"
    
    # Цвета для статусов
    STATUS_COLORS = {
        STATUS_READY: "blue",
        STATUS_LISTENING: "green",
        STATUS_THINKING: "yellow",
        STATUS_SPEAKING: "cyan",
        STATUS_ACTIVE: "magenta",
        STATUS_SLEEP: "red",
        STATUS_ERROR: "red",
    }
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки Arduino LED модуля
        self.arduino_enabled = config.get("hardware.led.arduino.enabled", True)
        self.arduino_port = config.get("hardware.led.arduino.port", "/dev/ttyACM0")
        self.arduino_baudrate = config.get("hardware.led.arduino.baudrate", 9600)
        
        self.arduino_serial: Optional[serial.Serial] = None
        self.current_status = None
    
    async def initialize(self):
        """Инициализация LED контроллера"""
        if not self.arduino_enabled:
            return
        
        try:
            self.arduino_serial = serial.Serial(
                self.arduino_port,
                self.arduino_baudrate,
                timeout=1
            )
            await asyncio.sleep(2)  # Ожидание инициализации Arduino
            self.logger.info(f"LED контроллер инициализирован на {self.arduino_port}")
        except Exception as e:
            self.logger.warning(f"Не удалось инициализировать LED контроллер: {e}")
    
    async def set_status(self, status: str):
        """
        Установка статуса робота
        
        Args:
            status: Статус робота (ready, listening, thinking, speaking, active, sleep, error)
        """
        if not self.arduino_serial or not self.arduino_serial.is_open:
            return
        
        self.current_status = status
        color = self.STATUS_COLORS.get(status, "white")
        
        try:
            # Отправка команды на Arduino
            # Формат: "SET_COLOR:color" или "SET_STATUS:status"
            command = f"SET_STATUS:{status}\n"
            self.arduino_serial.write(command.encode())
            self.logger.debug(f"LED статус установлен: {status} ({color})")
        except Exception as e:
            self.logger.error(f"Ошибка установки LED статуса: {e}")
    
    async def set_color(self, color: str):
        """
        Установка цвета LED
        
        Args:
            color: Цвет (red, green, blue, yellow, cyan, magenta, white)
        """
        if not self.arduino_serial or not self.arduino_serial.is_open:
            return
        
        try:
            command = f"SET_COLOR:{color}\n"
            self.arduino_serial.write(command.encode())
            self.logger.debug(f"LED цвет установлен: {color}")
        except Exception as e:
            self.logger.error(f"Ошибка установки LED цвета: {e}")
    
    async def blink(self, color: str, times: int = 3, interval: float = 0.5):
        """Мигание LED"""
        for _ in range(times):
            await self.set_color(color)
            await asyncio.sleep(interval)
            await self.set_color("off")
            await asyncio.sleep(interval)
        
        # Восстановление текущего статуса
        if self.current_status:
            await self.set_status(self.current_status)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.arduino_serial and self.arduino_serial.is_open:
            self.arduino_serial.close()
        self.logger.info("LED контроллер остановлен")

