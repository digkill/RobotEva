"""
Управление сенсорами (mmWave C1001, расширительная плата)
"""
import logging
import serial
import asyncio
from typing import Dict, Optional
import board
import adafruit_bme280
from adafruit_lsm6ds import LSM6DS33


class SensorManager:
    """Менеджер сенсоров"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки mmWave датчика
        self.mmwave_enabled = config.get("hardware.sensors.mmwave.enabled", True)
        self.mmwave_port = config.get("hardware.sensors.mmwave.port", "/dev/ttyUSB0")
        self.mmwave_baudrate = config.get("hardware.sensors.mmwave.baudrate", 115200)
        
        # Настройки расширительной платы
        self.expansion_enabled = config.get("hardware.sensors.expansion.enabled", True)
        
        self.mmwave_serial: Optional[serial.Serial] = None
        self.bme280: Optional[adafruit_bme280.Adafruit_BME280_I2C] = None
        self.lsm6ds: Optional[LSM6DS33] = None
    
    async def initialize(self):
        """Инициализация сенсоров"""
        try:
            # Инициализация mmWave датчика
            if self.mmwave_enabled:
                try:
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
                        self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
                        self.logger.info("BME280 (температура/влажность) инициализирован")
                    except Exception as e:
                        self.logger.warning(f"Не удалось инициализировать BME280: {e}")
                    
                    # LSM6DS33 (гироскоп/акселерометр)
                    try:
                        self.lsm6ds = LSM6DS33(i2c)
                        self.logger.info("LSM6DS33 (гироскоп/акселерометр) инициализирован")
                    except Exception as e:
                        self.logger.warning(f"Не удалось инициализировать LSM6DS33: {e}")
                
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

