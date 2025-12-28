"""
Управление LED индикатором (7-цветной мигающий)
"""
import logging
import serial
import asyncio
from typing import Optional
import lgpio


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
        
        # Получение конфигурации из GPIO маппинга
        led_config = config.get_gpio_mapping("gpio_pins.arduino_led")
        if led_config and led_config.get("enabled", False):
            # Использование GPIO напрямую
            self.use_gpio = True
            self.red_pin = led_config.get("red_pin", 18)
            self.green_pin = led_config.get("green_pin", 19)
            self.blue_pin = led_config.get("blue_pin", 13)
            self.pwm_frequency = led_config.get("pwm_frequency", 1000)
            self.arduino_serial = None
            self.gpio_chip = None
            self.red_handle = None
            self.green_handle = None
            self.blue_handle = None
        else:
            # Fallback на Arduino через Serial
            self.use_gpio = False
            self.arduino_enabled = config.get("hardware.led.arduino.enabled", True)
            self.arduino_port = config.get("hardware.led.arduino.port", "/dev/ttyACM0")
            self.arduino_baudrate = config.get("hardware.led.arduino.baudrate", 9600)
            self.arduino_serial = None
            self.gpio_chip = None
        
        self.current_status = None
    
    async def initialize(self):
        """Инициализация LED контроллера"""
        try:
            if self.use_gpio:
                # Инициализация через GPIO
                self.gpio_chip = lgpio.gpiochip_open(0)  # Открытие GPIO чипа 0
                
                # Настройка пинов как PWM выходы
                lgpio.gpio_claim_output(self.gpio_chip, self.red_pin)
                lgpio.gpio_claim_output(self.gpio_chip, self.green_pin)
                lgpio.gpio_claim_output(self.gpio_chip, self.blue_pin)
                
                # Инициализация PWM (если поддерживается)
                # Для простых GPIO используем software PWM через lgpio
                self.logger.info(f"LED контроллер инициализирован через GPIO (R={self.red_pin}, G={self.green_pin}, B={self.blue_pin})")
            else:
                # Инициализация через Arduino Serial
                if not self.arduino_enabled:
                    return
                
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
        self.current_status = status
        color = self.STATUS_COLORS.get(status, "white")
        
        try:
            if self.use_gpio:
                # Установка цвета через GPIO
                await self.set_color(color)
            else:
                # Отправка команды на Arduino через Serial
                if not self.arduino_serial or not self.arduino_serial.is_open:
                    return
                
                command = f"SET_STATUS:{status}\n"
                self.arduino_serial.write(command.encode())
            
            self.logger.debug(f"LED статус установлен: {status} ({color})")
        except Exception as e:
            self.logger.error(f"Ошибка установки LED статуса: {e}")
    
    async def set_color(self, color: str):
        """
        Установка цвета LED
        
        Args:
            color: Цвет (red, green, blue, yellow, cyan, magenta, white, off)
        """
        try:
            if self.use_gpio:
                # Установка цвета через GPIO PWM
                rgb_values = self._color_to_rgb(color)
                
                if self.gpio_chip is not None:
                    # Использование lgpio для управления GPIO
                    # Для PWM используем software PWM через duty cycle
                    # Максимальное значение для duty cycle зависит от частоты
                    max_duty = 100  # Процент
                    
                    # Установка красного канала
                    red_duty = int(rgb_values[0] * max_duty / 255)
                    lgpio.tx_pwm(self.gpio_chip, self.red_pin, self.pwm_frequency, red_duty)
                    
                    # Установка зеленого канала
                    green_duty = int(rgb_values[1] * max_duty / 255)
                    lgpio.tx_pwm(self.gpio_chip, self.green_pin, self.pwm_frequency, green_duty)
                    
                    # Установка синего канала
                    blue_duty = int(rgb_values[2] * max_duty / 255)
                    lgpio.tx_pwm(self.gpio_chip, self.blue_pin, self.pwm_frequency, blue_duty)
                    
                    self.logger.debug(f"LED цвет установлен через GPIO: {color} (R={rgb_values[0]}, G={rgb_values[1]}, B={rgb_values[2]})")
            else:
                # Отправка команды на Arduino через Serial
                if not self.arduino_serial or not self.arduino_serial.is_open:
                    return
                
                command = f"SET_COLOR:{color}\n"
                self.arduino_serial.write(command.encode())
                self.logger.debug(f"LED цвет установлен: {color}")
        except Exception as e:
            self.logger.error(f"Ошибка установки LED цвета: {e}")
    
    def _color_to_rgb(self, color: str) -> tuple:
        """
        Конвертация названия цвета в RGB значения
        
        Args:
            color: Название цвета
            
        Returns:
            Кортеж (R, G, B) со значениями 0-255
        """
        color_map = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
            "white": (255, 255, 255),
            "off": (0, 0, 0),
        }
        return color_map.get(color.lower(), (0, 0, 0))
    
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
        try:
            if self.use_gpio:
                # Отключение GPIO
                if self.gpio_chip is not None:
                    # Выключение всех каналов
                    await self.set_color("off")
                    # Освобождение GPIO пинов
                    lgpio.gpio_free(self.gpio_chip, self.red_pin)
                    lgpio.gpio_free(self.gpio_chip, self.green_pin)
                    lgpio.gpio_free(self.gpio_chip, self.blue_pin)
                    lgpio.gpiochip_close(self.gpio_chip)
            else:
                # Закрытие Serial соединения
                if self.arduino_serial and self.arduino_serial.is_open:
                    self.arduino_serial.close()
        except Exception as e:
            self.logger.error(f"Ошибка при очистке LED контроллера: {e}")
        
        self.logger.info("LED контроллер остановлен")

