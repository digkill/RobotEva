"""
Управление сенсорами (mmWave C1001, расширительная плата)
"""
import logging
import serial
import asyncio
from typing import Dict, Optional
import board
import adafruit_bme280
from adafruit_lsm6ds import LSM6DS


class SensorManager:
    """Менеджер сенсоров"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки mmWave датчика
        self.mmwave_enabled = config.get("hardware.sensors.mmwave.enabled", True)
        
        # Получение конфигурации из GPIO маппинга
        mmwave_config = config.get_gpio_mapping("gpio_pins.mmwave_c1001")
        if mmwave_config and mmwave_config.get("enabled", False):
            # Использование GPIO UART
            self.mmwave_use_gpio = True
            self.mmwave_tx_pin = mmwave_config.get("tx_pin", 14)
            self.mmwave_rx_pin = mmwave_config.get("rx_pin", 15)
            self.mmwave_uart = mmwave_config.get("uart", "uart0")
            self.mmwave_baudrate = mmwave_config.get("baudrate", 115200)
            self.mmwave_port = None
        else:
            # Fallback на USB/Serial
            self.mmwave_use_gpio = False
            self.mmwave_port = config.get("hardware.sensors.mmwave.port", "/dev/ttyUSB0")
            self.mmwave_baudrate = config.get("hardware.sensors.mmwave.baudrate", 115200)
            self.mmwave_tx_pin = None
            self.mmwave_rx_pin = None
            self.mmwave_uart = None
        
        # Настройки расширительной платы
        self.expansion_enabled = config.get("hardware.sensors.expansion.enabled", True)
        
        self.mmwave_serial: Optional[serial.Serial] = None
        self.bme280: Optional[adafruit_bme280.Adafruit_BME280_I2C] = None
        self.lsm6ds: Optional[LSM6DS] = None
    
    async def initialize(self):
        """Инициализация сенсоров"""
        try:
            # Инициализация mmWave датчика
            if self.mmwave_enabled:
                try:
                    if self.mmwave_use_gpio:
                        # Инициализация через GPIO UART
                        import serial as serial_lib
                        
                        # Определение устройства UART
                        uart_device_map = {
                            "uart0": "/dev/ttyAMA0",
                            "uart1": "/dev/ttyAMA1",
                            "uart2": "/dev/ttyAMA2",
                            "uart3": "/dev/ttyAMA3",
                            "uart4": "/dev/ttyAMA4",
                            "uart5": "/dev/ttyAMA5",
                        }
                        
                        uart_device = uart_device_map.get(self.mmwave_uart, "/dev/ttyAMA0")
                        
                        self.mmwave_serial = serial_lib.Serial(
                            uart_device,
                            self.mmwave_baudrate,
                            timeout=1
                        )
                        self.logger.info(f"mmWave датчик C1001 инициализирован через GPIO UART ({self.mmwave_uart}, TX={self.mmwave_tx_pin}, RX={self.mmwave_rx_pin})")
                    else:
                        # Инициализация через USB/Serial
                        self.mmwave_serial = serial.Serial(
                            self.mmwave_port,
                            self.mmwave_baudrate,
                            timeout=1
                        )
                        self.logger.info(f"mmWave датчик C1001 инициализирован на {self.mmwave_port}")
                except Exception as e:
                    self.logger.warning(f"Не удалось инициализировать mmWave датчик: {e}")
            
            # Инициализация расширительной платы
            if self.expansion_enabled:
                try:
                    i2c = board.I2C()
                    
                    # BME280 (температура и влажность)
                    try:
                        # Попробуем разные варианты импорта
                        try:
                            from adafruit_bme280 import basic as adafruit_bme280_basic
                            self.bme280 = adafruit_bme280_basic.Adafruit_BME280_I2C(i2c)
                        except (ImportError, AttributeError):
                            # Старый API
                            self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
                        self.logger.info("BME280 (температура/влажность) инициализирован")
                    except Exception as e:
                        self.logger.warning(f"Не удалось инициализировать BME280: {e}")
                    
                    # LSM6DS (гироскоп/акселерометр)
                    try:
                        # LSM6DS - это базовый класс, нужно использовать конкретную реализацию
                        try:
                            from adafruit_lsm6ds.lsm6ds33 import LSM6DS33
                            self.lsm6ds = LSM6DS33(i2c)
                            self.logger.info("LSM6DS33 (гироскоп/акселерометр) инициализирован")
                        except (ImportError, AttributeError):
                            # Попробуем другой вариант
                            self.lsm6ds = LSM6DS(i2c)
                            self.logger.info("LSM6DS (гироскоп/акселерометр) инициализирован")
                    except Exception as e:
                        self.logger.warning(f"Не удалось инициализировать LSM6DS: {e}")
                
                except Exception as e:
                    self.logger.warning(f"Ошибка инициализации расширительной платы: {e}")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации сенсоров: {e}")
    
    async def get_presence_data(self) -> Dict:
        """
        Получение данных от mmWave датчика
        
        Returns:
            Словарь с данными о присутствии:
            - human_detected: bool
            - sleep_detected: bool
            - heart_rate: Optional[float]
            - stationary_body: bool
        """
        data = {
            "human_detected": False,
            "sleep_detected": False,
            "heart_rate": None,
            "stationary_body": False
        }
        
        if not self.mmwave_serial or not self.mmwave_serial.is_open:
            return data
        
        try:
            # Чтение данных из mmWave датчика
            # Формат данных зависит от протокола датчика C1001
            if self.mmwave_serial.in_waiting > 0:
                line = self.mmwave_serial.readline().decode('utf-8', errors='ignore').strip()
                
                # Парсинг данных (формат зависит от протокола датчика)
                # Примерный формат: "HUMAN:1,SLEEP:0,HR:72,STAT:1"
                if line:
                    parts = line.split(',')
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':', 1)
                            if key == 'HUMAN':
                                data["human_detected"] = value == '1'
                            elif key == 'SLEEP':
                                data["sleep_detected"] = value == '1'
                            elif key == 'HR':
                                try:
                                    data["heart_rate"] = float(value)
                                except ValueError:
                                    pass
                            elif key == 'STAT':
                                data["stationary_body"] = value == '1'
        
        except Exception as e:
            self.logger.error(f"Ошибка чтения данных mmWave: {e}")
        
        return data
    
    async def get_temperature(self) -> Optional[float]:
        """Получение температуры с BME280"""
        if self.bme280:
            try:
                return self.bme280.temperature
            except Exception as e:
                self.logger.error(f"Ошибка чтения температуры: {e}")
        return None
    
    async def get_humidity(self) -> Optional[float]:
        """Получение влажности с BME280"""
        if self.bme280:
            try:
                return self.bme280.humidity
            except Exception as e:
                self.logger.error(f"Ошибка чтения влажности: {e}")
        return None
    
    async def get_acceleration(self) -> Optional[tuple]:
        """Получение данных акселерометра"""
        if self.lsm6ds:
            try:
                return (
                    self.lsm6ds.acceleration[0],
                    self.lsm6ds.acceleration[1],
                    self.lsm6ds.acceleration[2]
                )
            except Exception as e:
                self.logger.error(f"Ошибка чтения акселерометра: {e}")
        return None
    
    async def get_gyro(self) -> Optional[tuple]:
        """Получение данных гироскопа"""
        if self.lsm6ds:
            try:
                return (
                    self.lsm6ds.gyro[0],
                    self.lsm6ds.gyro[1],
                    self.lsm6ds.gyro[2]
                )
            except Exception as e:
                self.logger.error(f"Ошибка чтения гироскопа: {e}")
        return None
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.mmwave_serial and self.mmwave_serial.is_open:
            self.mmwave_serial.close()
        
        self.logger.info("Сенсоры остановлены")

